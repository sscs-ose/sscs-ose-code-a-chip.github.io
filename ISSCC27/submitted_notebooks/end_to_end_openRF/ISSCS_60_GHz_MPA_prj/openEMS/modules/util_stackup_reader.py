#
# Copyright 2025 Volker Muehlhaus and IHP PDK Authors
#
# Licensed under the GNU General Public License, Version 3.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.gnu.org/licenses/gpl-3.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
########################################################################


# Read XML file with SG13G2 stackup

# File history: 
# Initial version 20 Nov 2024  Volker Muehlhaus 
# Added support for sheet resistance 07 Oct 2025 Volker Muehlhaus 
# Added docstrings 
# 20 Nov 2025: added functionality to get relative positions between metals
# 10 Aug 2026: added derived layer option
# 10 Aug 2026: added Oversize option for derived layers (grow/shrink outline)
# 15 Aug 2026: added Reference/ReferenceEdge option for reference-relative Layer positioning
# 15 Aug 2026: added Reference/ReferenceEdge option for reference-relative Dielectric positioning
# 15 Aug 2026: fixed register_metals_inside() to register a metal by its zmin alone, so a
#              metal whose zmax overflows past its own dielectric (e.g. via Reference) is
#              still registered somewhere instead of silently dropped from metals_inside
# 15 Aug 2026: added a schemaVersion check - prints a warning (does not abort) when a
#              stackup file declares a schemaVersion newer than SUPPORTED_SCHEMA_VERSION
# 16 Aug 2026: fixed register_metals_inside() to compare zmin/zmax with a small epsilon
#              tolerance, so floating-point noise between two independently-accumulated
#              z values that represent the same physical boundary can no longer misassign
#              a boundary-sitting metal (zero real overlap) to the dielectric below it
# 18 Aug 2026: added <Variables>/<Variable> and "="-prefixed expression support, usable in
#              any attribute value anywhere in the file (Materials, Dielectrics, Layers,
#              Substrate, DerivedLayers, Tables) - see doc/XML_stackup_format section
#              "<Variables>"; bumped schema to "3.1"
# 18 Aug 2026: added variable_overrides parameter to read_substrate()/parse_substrate(), so
#              an external caller (e.g. a parametric sweep script) can override a <Variable>'s
#              value without editing the XML file - see variables_list.apply_overrides()
# 18 Aug 2026: made the "variables" argument optional (default None -> empty variables_list)
#              on stackup_material/dielectric_layer/metal_layer/derived_layer/thermal_table,
#              so a caller built before <Variables> existed (e.g. setupEM's stackup_editor.py,
#              which constructs these directly rather than via parse_substrate()) keeps working
#              unchanged for ordinary files, instead of every call raising TypeError outright

__version__ = "1.7.2"

import os
import math
import ast
import operator
import xml.etree.ElementTree

# Highest <Stackup schemaVersion="..."> this reader understands. schemaVersion is otherwise
# informational only (nothing here branches on it) - this is used solely to warn when a file
# was written by a newer gds2palace than the one doing the reading, since such a file may use
# attributes this version of the reader doesn't know about yet. Bump this whenever a schema
# change actually needs a newer reader to be interpreted correctly (e.g. Reference/
# ReferenceEdge bumped the format to "3.0"; <Variables>/"=" expressions bumped it to "3.1").
SUPPORTED_SCHEMA_VERSION = "3.1"


def _parse_schema_version (version_string):
  """Parse a schemaVersion string like "3.0" into a tuple of ints for numeric comparison
     (plain string comparison would wrongly rank "10.0" below "9.0").
  Args:
      version_string (string): e.g. "3.0", or None/malformed
  Returns:
      tuple of int, or None if version_string isn't a dotted-number version
  """
  if not version_string:
    return None
  try:
    return tuple(int(part) for part in version_string.split("."))
  except ValueError:
    return None


def check_schema_version (substrate_root):
  """Warn (print only, does not raise/exit) if substrate_root's schemaVersion is newer than
     SUPPORTED_SCHEMA_VERSION - such a file may have been written with a newer gds2palace
     and could use attributes this reader doesn't understand yet. Silently does nothing if
     schemaVersion is missing or doesn't parse as a dotted-number version.
  Args:
      substrate_root (xml.etree.ElementTree.Element): root <Stackup> element
  """
  file_version = substrate_root.get("schemaVersion")
  file_tuple = _parse_schema_version(file_version)
  supported_tuple = _parse_schema_version(SUPPORTED_SCHEMA_VERSION)
  if file_tuple is not None and supported_tuple is not None and file_tuple > supported_tuple:
    print(f'WARNING: This stackup file has schemaVersion="{file_version}", newer than '
          f'schemaVersion="{SUPPORTED_SCHEMA_VERSION}" supported by this version of '
          f'gds2palace (util_stackup_reader.py {__version__}). It may use attributes this '
          f'reader does not understand yet - consider upgrading gds2palace.')

def _make_comment_preserving_parser():
  """XML parser that keeps <!-- comments --> as Comment nodes in the tree, instead of
     silently dropping them (the default xml.etree behavior). Needed so that editors
     which load, edit, and save a stackup file back to disk don't lose comments that
     live inside sections they don't touch (e.g. DerivedLayers).
  """
  target = xml.etree.ElementTree.TreeBuilder(insert_comments=True)
  return xml.etree.ElementTree.XMLParser(target=target)


# -------------------- "=" expression evaluation ---------------------------
#
# Any attribute value starting with "=" is a restricted-arithmetic expression, evaluated
# against already-resolved <Variables> (see the "variables"/"variables_list" classes below).
# A bare variable reference is just the trivial one-token case of an expression (e.g. "=w").
# This grammar deliberately supports only +,-,*,/,**, unary +/-, parentheses, numeric and
# string literals, and bare names - no function calls, string concatenation, comparisons,
# subscripts, or attribute access - so ast.parse()+a restricted node visitor is a safe
# evaluator, never Python's own eval()/exec().

_ALLOWED_BINOPS = {
  ast.Add: operator.add,
  ast.Sub: operator.sub,
  ast.Mult: operator.mul,
  ast.Div: operator.truediv,
  ast.Pow: operator.pow,
}

_ALLOWED_UNARYOPS = {
  ast.UAdd: operator.pos,
  ast.USub: operator.neg,
}


class _ExpressionError (Exception):
  """A "="-expression is not syntactically valid, or uses syntax outside the restricted
     grammar (e.g. a function call), or mixes a string-typed variable into arithmetic.
     Callers catch this to add file/attribute context before print+exit(1).
  """
  pass


class _UndefinedVariableError (Exception):
  """A "="-expression's ast.Name node isn't in the values dict passed to evaluation. Raised
     both for a genuinely undefined variable name and (during variables_list.resolve_all()'s
     dependency worklist) for a variable that exists but isn't resolved yet - the two cases
     are told apart by the caller, which knows which names actually exist.
  """
  def __init__ (self, name):
    super().__init__(name)
    self.name = name


def _expression_names (expr_str):
  """Parse a "="-expression's body (leading "=" already stripped) and return the set of bare
     identifier names it references, without evaluating it. Used by variable dependency
     resolution to check readiness before actually evaluating.
  Args:
      expr_str (string): expression text, leading "=" already stripped
  Returns:
      set of string: variable names referenced in the expression
  Raises:
      _ExpressionError: if expr_str is not syntactically a valid expression
  """
  try:
    tree = ast.parse(expr_str, mode="eval")
  except SyntaxError as e:
    raise _ExpressionError(str(e))
  return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}


def _eval_expression_ast (node, values):
  """Recursively evaluate one ast node under the restricted expression grammar.
  Args:
      node (ast.AST): node to evaluate
      values (dict): variable name -> already-resolved value (float or str)
  Returns:
      float or str
  Raises:
      _ExpressionError: disallowed syntax, or a string value used in arithmetic
      _UndefinedVariableError: a Name node not present in `values`
  """
  if isinstance(node, ast.Expression):
    return _eval_expression_ast(node.body, values)
  if isinstance(node, ast.Constant) and isinstance(node.value, (int, float, str)):
    return node.value
  if isinstance(node, ast.Name):
    if node.id not in values:
      raise _UndefinedVariableError(node.id)
    return values[node.id]
  if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_BINOPS:
    left = _eval_expression_ast(node.left, values)
    right = _eval_expression_ast(node.right, values)
    if isinstance(left, str) or isinstance(right, str):
      raise _ExpressionError('a string-typed variable cannot be used in arithmetic')
    return _ALLOWED_BINOPS[type(node.op)](left, right)
  if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_UNARYOPS:
    operand = _eval_expression_ast(node.operand, values)
    if isinstance(operand, str):
      raise _ExpressionError('a string-typed variable cannot be used in arithmetic')
    return _ALLOWED_UNARYOPS[type(node.op)](operand)
  raise _ExpressionError('unsupported syntax (only +,-,*,/,**, unary +/-, parentheses, '
                          'numbers, strings, and variable names are allowed)')


def _eval_expression (expr_str, values):
  """Evaluate a "="-expression's body (leading "=" already stripped) against a dict of
     already-resolved variable values.
  Args:
      expr_str (string): expression text
      values (dict): variable name -> value (float or str)
  Returns:
      float or str: the expression result
  Raises:
      _ExpressionError, _UndefinedVariableError
  """
  try:
    tree = ast.parse(expr_str, mode="eval")
  except SyntaxError as e:
    raise _ExpressionError(str(e))
  return _eval_expression_ast(tree, values)


def _infer_literal_value (raw_value):
  """Infer number vs. string for a plain (non-"=") Variable Value: parses as float -> number,
     otherwise string. Mirrors how every other numeric attribute in this file is parsed
     (bare float()), just without assuming success.
  Args:
      raw_value (string): raw Value attribute text
  Returns:
      float or str
  """
  try:
    return float(raw_value)
  except (TypeError, ValueError):
    return raw_value


def resolve_attr (data, key, default, variables):
  """Return an attribute's value: `default` if the attribute is absent, the raw string
     unchanged if it's a plain literal, or the result of evaluating a "="-prefixed expression
     against `variables` if present. This is the single choke point every attribute value in
     the stackup file passes through, so "=" expressions work uniformly everywhere (Materials,
     Dielectrics, Layers, Substrate, DerivedLayers, Tables) without each call site needing its
     own logic. A numeric expression result is returned as its str() so every existing
     float(...) call site keeps working unchanged; a string result (a plain literal without
     "=", or a string-typed variable) is returned as-is.
  Args:
      data (xml.etree.ElementTree.Element): source of the raw attribute
      key (string): attribute name
      default: value to return if the attribute is absent
      variables (variables_list): fully-resolved variables to evaluate expressions against
  Returns:
      string, or `default` unchanged if the attribute is absent
  """
  raw = data.get(key)
  if raw is None:
    return default
  if not (isinstance(raw, str) and raw.startswith("=")):
    return raw
  try:
    result = _eval_expression(raw[1:], variables.as_dict())
  except _UndefinedVariableError as e:
    print('ERROR: attribute ', key, '="', raw, '" references undefined variable "', e.name, '"')
    exit(1)
  except _ExpressionError as e:
    print('ERROR: attribute ', key, '="', raw, '" is an invalid expression: ', str(e))
    exit(1)
  return str(result) if isinstance(result, (int, float)) else result


def resolve_int_attr (data, key, variables):
  """Like resolve_attr(), but for GDSII layer-number attributes (<Layer Layer="...">,
     <DerivedLayer Layer="...">, <Operand Layer="...">, <Dielectric Boundary="...">): the
     resolved value must be an integer-valued number - an expression may legitimately produce
     e.g. 126.0 from variable arithmetic (fine), but a genuinely fractional result is an error,
     not a silent truncation. Returns the value as a plain integer string, so existing
     int(...)/string-equality call sites are unaffected whether the attribute was a literal or
     an expression.
  Args:
      data (xml.etree.ElementTree.Element): source of the raw attribute
      key (string): attribute name
      variables (variables_list): fully-resolved variables to evaluate expressions against
  Returns:
      string: the layer number as a plain integer string, or None if the attribute is absent
  """
  resolved = resolve_attr(data, key, None, variables)
  if resolved is None:
    return None
  try:
    numeric_value = float(resolved)
  except (TypeError, ValueError):
    print('ERROR: attribute ', key, '="', resolved, '" must be a GDSII layer number (integer)')
    exit(1)
  if numeric_value != int(numeric_value):
    print('ERROR: attribute ', key, '="', resolved, '" evaluates to ', numeric_value,
          ', which is not a whole number - GDSII layer numbers must be integers')
    exit(1)
  return str(int(numeric_value))


# -------------------- variables ---------------------------

class variable:
  """
    named value (number or string; a plain literal, or a "="-prefixed expression that may
    reference other variables) that any other attribute in the stackup file can refer to.
  """

  def __init__ (self, data):
    """create variable object from XML data line

    Args:
        data (xml.etree.ElementTree.Element): "Variable" XML element, required attributes
          "Name" and "Value"; optional "Type" ("number" or "string"). For a plain-literal
          Value, an explicit Type controls parsing (Type="string" keeps a numeric-looking
          literal as text instead of inferring it as a number); if omitted, Type is inferred
          by trying to parse Value as a number. A "Value" starting with "=" is an expression,
          resolved later by resolve() once every variable it depends on is itself resolved -
          there Type cannot override the computed result's type, so it is only validated
          against it (a mismatch is an error). Plain literals have no dependency on other
          variables, so they're resolvable immediately.
    """
    self.name = data.get("Name")
    self.raw_value = data.get("Value")

    type_attr = data.get("Type")
    self.declared_type = type_attr.lower() if type_attr is not None else None
    if self.declared_type not in (None, "number", "string"):
      print('ERROR: Variable ', self.name, ' has invalid Type="', type_attr, '", must be number or string')
      exit(1)

    self.value = None      # set once resolved: float or str
    self.resolved = False
    self.overridden = False   # set True by apply_override(), for __str__/debugging
    self.is_expression = isinstance(self.raw_value, str) and self.raw_value.startswith("=")

    if not self.is_expression:
      # plain literal: resolvable immediately, no dependency on other variables. Explicit
      # Type controls parsing here (not just validates), since a literal's textual form is
      # inherently ambiguous - "123" could be meant as either a number or a string, and
      # Type="string" is precisely how to force the latter.
      if self.declared_type == "string":
        self.value = self.raw_value
      elif self.declared_type == "number":
        try:
          self.value = float(self.raw_value)
        except (TypeError, ValueError):
          print('ERROR: Variable ', self.name, ' declared Type="number" but Value="', self.raw_value, '" does not parse as a number')
          exit(1)
      else:
        self.value = _infer_literal_value(self.raw_value)
      self.resolved = True


  def _check_declared_type (self):
    """If Type was given explicitly, validate it against the actual evaluated type of an
       expression-valued self.value; ERROR/exit(1) on mismatch. Only meaningful for
       expressions - a literal's Type already controlled parsing in __init__, so it can never
       mismatch by the time this would apply to one.
    """
    actual_type = "number" if isinstance(self.value, float) else "string"
    if self.declared_type is not None and self.declared_type != actual_type:
      print('ERROR: Variable ', self.name, ' declared Type="', self.declared_type,
            '" but Value evaluates to a ', actual_type)
      exit(1)


  def resolve (self, variables_list_):
    """Resolve an expression-valued variable using already-resolved variables. No-op if
       already resolved (plain literals are resolved in __init__).
    Args:
        variables_list_ (variables_list): variables to look up by name inside the expression
    """
    if self.resolved:
      return
    try:
      self.value = _eval_expression(self.raw_value[1:], variables_list_.as_dict())
    except _UndefinedVariableError as e:
      # defensive: variables_list.resolve_all() is expected to only call resolve() once every
      # variable this one's expression references is itself already resolved
      print('ERROR: Variable ', self.name, ' references variable "', e.name, '" which is not yet resolved')
      exit(1)
    except _ExpressionError as e:
      print('ERROR: Variable ', self.name, ' has an invalid expression: ', str(e))
      exit(1)
    self._check_declared_type()
    self.resolved = True


  def apply_override (self, new_value):
    """Replace this variable's resolved value with an externally supplied override (e.g. from
       a parametric sweep script). Takes effect immediately, before resolve_all() runs - no
       expression parsing or dependency resolution needed, since the override IS the final
       value. Bypasses whatever the XML itself declared for this variable (a literal or a
       "="-expression, doesn't matter which). self.declared_type (if the XML gave one) is
       still validated against it.
    Args:
        new_value: override value - a plain float/int for a numeric variable, or a str for a
          string-typed one
    """
    self.value = new_value if isinstance(new_value, str) else float(new_value)
    self.resolved = True
    self.overridden = True
    self._check_declared_type()


  def __str__ (self):
    """String representation of variable, useful for debugging
    Returns:
        string: String representation of variable
    """
    overridden_suffix = ' (overridden)' if self.overridden else ''
    return '      Variable Name=' + self.name + ' Value=' + str(self.value) + overridden_suffix



class variables_list:
  """
    list of variable objects, with dependency resolution ("=" expressions may reference
    other variables regardless of declaration order) and lookup by name.
  """

  def __init__ (self):
    """Create empty list
    """
    self.variables = []

  def append (self, var):
    """Append one variable
    Args:
        var (variable): variable to add
    """
    self.variables.append(var)

  def get_by_name (self, name_to_find):
    """find variable object from name
    Args:
        name_to_find (string): Name as specified in XML data line
    Returns:
        variable: the variable with that name, or None
    """
    for var in self.variables:
      if var.name == name_to_find:
        return var
    return None

  def as_dict (self):
    """Values of every resolved variable, for evaluating "=" expressions elsewhere in the
       stackup file. Only meaningful after resolve_all() has run.
    Returns:
        dict: variable name -> float or str
    """
    return {var.name: var.value for var in self.variables if var.resolved}

  def apply_overrides (self, overrides):
    """Apply externally supplied variable-value overrides (e.g. from a parametric sweep
       script), before resolve_all() runs. Every override key must name a <Variable> already
       defined in the file - ERROR/exit(1) on an unknown name, so a typo in the override dict
       is caught immediately instead of silently doing nothing or defining an unused variable.
    Args:
        overrides (dict): variable name -> plain override value (float/int/str) - see
          variable.apply_override()
    """
    if not overrides:
      return
    for name, new_value in overrides.items():
      var = self.get_by_name(name)
      if var is None:
        print('ERROR: variable_overrides references variable "', name, '" which is not defined in this stackup file')
        exit(1)
      var.apply_override(new_value)


  def resolve_all (self):
    """Resolve every variable's value, in dependency order (repeat until no progress) - same
       approach as metal_layers_list.resolve_references()/derived_layers_list.get_ordered().
       An expression referencing a name that is never defined as a Variable is a hard error
       reported immediately (not left to fall out as "circular"); a name that exists but isn't
       resolved yet just defers this variable to a later pass. Any variable already resolved
       via apply_override() beforehand is skipped here (see the "not var.resolved" filter
       below), so an override transparently short-circuits whatever the XML itself declared.
    """
    remaining = [var for var in self.variables if not var.resolved]

    while remaining:
      progress = False
      still_remaining = []

      for var in remaining:
        try:
          needed = _expression_names(var.raw_value[1:])
        except _ExpressionError as e:
          print('ERROR: Variable ', var.name, ' has an invalid expression: ', str(e))
          exit(1)

        missing = [name for name in needed if self.get_by_name(name) is None]
        if missing:
          print('ERROR: Variable ', var.name, ' references undefined variable(s): ', missing)
          exit(1)

        pending = [name for name in needed if not self.get_by_name(name).resolved]
        if not pending:
          var.resolve(self)
          progress = True
        else:
          still_remaining.append(var)

      if not progress:
        unresolved_names = [var.name for var in still_remaining]
        print('ERROR: Circular reference among Variables: ', unresolved_names)
        exit(1)

      remaining = still_remaining


# -------------------- material types ---------------------------

class stackup_material:
  """
    stackup material object, can be dielectric or metal with conductivity or sheet with Ohm/square
  """
    
  def __init__ (self, data, variables=None):
    """create stackup material object from XML data line

    Args:
        data (string): line from XML data, required parameters are "Name" and "Type" strings. Optional: "Permittivity","DielectricLossTangent","Conductivity","Rs","Color"
        variables (variables_list, optional): fully-resolved <Variables>, for resolving any
          "="-prefixed expression among this material's attributes. Defaults to an empty
          variables_list if omitted - fine for a file with no expressions; a caller that omits
          this for a file that does use one gets a clear _UndefinedVariableError-driven message
          instead of this constructor raising TypeError outright.
    """
    if variables is None:
      variables = variables_list()


    self.name = resolve_attr(data, "Name", None, variables)
    self.type = resolve_attr(data, "Type", None, variables).upper()

    self.eps   = float(resolve_attr(data, "Permittivity", 1, variables))
    self.tand  = float(resolve_attr(data, "DielectricLossTangent", 0, variables))
    self.sigma = float(resolve_attr(data, "Conductivity", 0, variables))
    self.Rs    = float(resolve_attr(data, "Rs", 0, variables))
    self.density = float(resolve_attr(data, "Density", 1, variables))
    self.color = resolve_attr(data, "Color", None, variables)  # no default here, will be handled later

    self.thermalcond = float(resolve_attr(data, "ThermalConductivity", 0, variables))
    self.thermaltablename = resolve_attr(data, "ThermalConductivityTable", "", variables)
    self.thermaltable = None


  def __str__ (self):
    """String representation of stackup_material, useful for debugging

    Returns:
        string: String representation of stackup_material
    """
    # string representation 
    mystr = '      Material Name=' + self.name + ' Type=' + self.type +' Permittivity=' + str(self.eps) + ' DielectricLossTangent=' +  str(self.tand) + ' Conductivity=' +  str(self.sigma) + ' ThermalConductivity=' +  str(self.thermalcond)  + ' Color = ' + self.color
    return mystr



class stackup_materials_list:
  """
    structure with list of stackup material objects (.materials) and value of maximum permittivy (.eps_max)
  """

  def __init__ (self):
    """Create empty structure. 
    """
    self.materials = []      # list with material objects
    self.eps_max   = 0
    
  def append (self, material):
    """Append one material
    Args:
        material (stackup_material): material to add
    """

    # append material
    self.materials.append (material)
    # set maximum permittivity in model
    self.eps_max = max(self.eps_max, material.eps)
  

  def get_by_name (self, materialname):
    """find material object from materialname
    Args:
        materialname (string): Name as specified in XML data line
    Returns:
        stackup_material: the material with that name
    """
  
    # find material object from materialname
    found = None
    for material in self.materials:
      if material.name.upper() == materialname.upper():
        found = material
    return found    


# -------------------- dielectrics ---------------------------

class dielectric_layer:
  """
    dielectric layer object. Holds information on stackup layers that are always there, without drawing them explicitely in GDSII
  """
    
  def __init__ (self, data, variables=None):
    """create stackup layer object (usually dielectric or semiconductor) from XML data line

    Args:
        data (string): line from XML data, required parameters: "Name","Material", and one of
          "Thickness"/"Zmax" (see below); optional parameter "Boundary" for bounding layer number.
          Optional "Reference"/"ReferenceEdge": if "Reference" names another Dielectric, "Zmin"
          (default 0) and "Zmax" (default Zmin+Thickness) are offsets from that Dielectric's edge
          instead of absolute z, resolved later by resolve().
        variables (variables_list, optional): fully-resolved <Variables>, for resolving any
          "="-prefixed expression among this dielectric's attributes. Defaults to an empty
          variables_list if omitted - see stackup_material.__init__ for why.
    """
    if variables is None:
      variables = variables_list()
    self.name = resolve_attr(data, "Name", None, variables)
    self.material = resolve_attr(data, "Material", None, variables)

    self.reference = resolve_attr(data, "Reference", None, variables) or None
    self.reference_edge = resolve_attr(data, "ReferenceEdge", "Top", variables)
    # set True by dielectric_layers_list._assign_implicit_references() for a dielectric that had
    # no explicit Reference in the XML but got one auto-derived from implicit Thickness-stacking
    self.reference_is_auto = False

    zmin_attr = resolve_attr(data, "Zmin", None, variables)
    zmax_attr = resolve_attr(data, "Zmax", None, variables)
    thickness_attr = resolve_attr(data, "Thickness", None, variables)

    if self.reference:
      # Reference set: Zmin/Zmax (if given) are offsets from the reference edge. Unlike <Layer>,
      # both aren't required - Dielectrics keep Thickness as their primary size: Zmin defaults to
      # 0 (start right at the reference edge, the common case) and Zmax defaults to Zmin+Thickness.
      self.offset_zmin = float(zmin_attr) if zmin_attr is not None else 0.0
      if zmax_attr is not None:
        self.offset_zmax = float(zmax_attr)
      elif thickness_attr is not None:
        self.offset_zmax = self.offset_zmin + float(thickness_attr)
      else:
        print('ERROR: Dielectric ', self.name, ' has Reference set but neither Zmax nor Thickness to size it')
        exit(1)
      self.zmin = None
      self.zmax = None
      self.thickness = None  # set once resolved
      self.absolute_zpos = False
      self.resolved = False
    elif not (zmin_attr is None or zmax_attr is None):
      # we have a valid absolute position, use that instead of stacking everything one after another
      self.zmin = float(zmin_attr)
      self.zmax = float(zmax_attr)
      self.thickness = self.zmax - self.zmin
      self.absolute_zpos = True
      self.resolved = True
    else:
      # No Reference and no absolute zmin/zmax: position results from stacking dielectric by
      # order in file, using their thickness values - either directly (z Position set later by
      # calculate_zpositions()), or via a Reference auto-assigned to the dielectric below it
      # (see _assign_implicit_references()), resolved the same way as an explicit Reference.
      self.zmin = None
      self.zmax = None
      self.thickness  = float(thickness_attr)
      self.absolute_zpos = False
      self.resolved = False
      # offsets for resolve(): used as-is if _assign_implicit_references() later gives this
      # dielectric a Reference; if it stays the anchor (Reference stays None), resolve()
      # applies these against a base of 0, i.e. zmin=0, zmax=Thickness - same as legacy
      self.offset_zmin = 0.0
      self.offset_zmax = self.thickness

    self.is_top = False
    self.is_bottom = False
    self.gdsboundary = resolve_int_attr(data, "Boundary", variables)  # optional entry in stackup file

    self.metals_inside = [] # metals that are located inside this dielectric, set by function

  def resolve (self, dielectrics_list):
    """Resolve a Reference-based (explicit or auto-assigned) dielectric's zmin/zmax from an
       offset into an absolute z position. No-op if already resolved (absolute-position
       dielectrics are resolved in __init__). A dielectric with no Reference at all (the anchor
       of an implicit stacking run) resolves against z=0, matching the legacy behavior of
       dielectric_layers_list.calculate_zpositions() before Reference existed.
    Args:
        dielectrics_list (dielectric_layers_list): dielectrics to search for a Reference match
    """
    if self.resolved:
      return

    if self.reference is None:
      base = 0.0
    else:
      target = dielectrics_list.get_by_name(self.reference)
      if target is None:
        print('ERROR: Dielectric ', self.name, ' has Reference="', self.reference, '" which matches no Dielectric')
        exit(1)

      edge = (self.reference_edge or "Top").upper()
      if edge not in ("TOP", "BOTTOM"):
        print('ERROR: Dielectric ', self.name, ' has invalid ReferenceEdge="', self.reference_edge, '", must be Top or Bottom')
        exit(1)

      if not target.resolved:
        # defensive: caller (dielectric_layers_list.resolve_references) is expected to only
        # call resolve() once a Reference target is already resolved
        print('ERROR: Dielectric ', self.name, ' references Dielectric "', self.reference, '" which is not yet resolved')
        exit(1)
      base = target.zmax if edge == "TOP" else target.zmin

    self.zmin = base + self.offset_zmin
    self.zmax = base + self.offset_zmax
    self.thickness = self.zmax - self.zmin
    self.resolved = True


  def get_planar_metals_inside (self):
    """evaluates metals_inside list and returns only items that are conductor or sheet (no via, not dielectric via)
    Returns:
        list of metal_layer: metals that are conductor or sheet
    """
    planar_metals = []
    for metal in self.metals_inside:
      if metal.is_metal or metal.is_sheet:
        planar_metals.append(metal)
    return planar_metals


  def __str__ (self):
    """String representation of dielectric_layer, useful for debugging
    Returns:
        string: String representation of stackup_material
    """
    enclosed_metal_names = []
    for metal in self.metals_inside:
      enclosed_metal_names.append(metal.name)

    mystr = '      Dielectric Name=' + self.name + ' Material=' + self.material +' Thickness=' \
            + str(self.thickness) + ' Zmin=' +  str(self.zmin) + ' Zmax=' +  str(self.zmax) \
            + ' Metals inside: ' + str(enclosed_metal_names)
            
    return mystr



class dielectric_layers_list:
  """
    list that holds all dielectric layer objects
  """

  def __init__ (self):
    """Initialize empty list
    """
    self.dielectrics = []      # list with dielectric objects
    
  def append (self, dielectric, materials_list ):
    """Append one dielectric to the list

    Args:
        dielectric (dielectric_layer): the dielectric that is appended
        materials_list (_type_): not used
    """

    self.dielectrics.append (dielectric)


  def _assign_implicit_references (self):
    """For a dielectric with no explicit Reference and no absolute position (pure Thickness-only
       stacking), auto-assign Reference = the nearest dielectric below it in file order that is
       ALSO pure-Thickness-only, ReferenceEdge="Top" - reproducing exactly what the legacy
       accumulate-by-file-order algorithm computed, just expressed as an explicit Reference chain.

       Deliberately preserves that legacy algorithm's quirk: an absolute-position or
       explicit-Reference dielectric in between is transparent to this chain (skipped over, not
       used as a stacking basis) - a pure-implicit dielectric right after one of those still
       chains to the nearest pure-implicit dielectric further below, not to the one immediately
       adjacent in the file. The very first pure-implicit dielectric encountered (nothing
       pure-implicit below it) stays anchored with no Reference at all (resolve() treats that
       as z=0), same as the legacy algorithm's starting point.
    """
    last_pure_implicit = None
    for dielectric in reversed(self.dielectrics):
      is_absolute = dielectric.absolute_zpos
      has_explicit_reference = dielectric.reference is not None
      if not is_absolute and not has_explicit_reference:
        if last_pure_implicit is not None:
          dielectric.reference = last_pure_implicit.name
          dielectric.reference_edge = "Top"
          dielectric.reference_is_auto = True
        last_pure_implicit = dielectric
      # absolute or explicit-Reference dielectrics don't affect last_pure_implicit - they're
      # transparent to this tracking, exactly like the legacy accumulator skipped them


  def resolve_references (self):
    """Resolve every dielectric's zmin/zmax: absolute-position ones are already resolved at
       construction; the rest (Reference-based, explicit or auto-assigned) are resolved in
       dependency order, modeled on metal_layers_list.resolve_references() for Layers.
    """
    remaining = [dielectric for dielectric in self.dielectrics if not dielectric.resolved]

    while remaining:
      progress = False
      still_remaining = []

      for dielectric in remaining:
        target = self.get_by_name(dielectric.reference) if dielectric.reference is not None else None
        # ready to resolve once there's no Reference at all (the z=0 anchor case), or the
        # Reference names a dielectric that is itself already resolved; an unresolvable name is
        # also "ready" here so resolve() reports the precise error immediately instead of stalling
        if dielectric.reference is None or target is None or target.resolved:
          dielectric.resolve(self)
          progress = True
        else:
          still_remaining.append(dielectric)

      if not progress:
        unresolved_names = [dielectric.name for dielectric in still_remaining]
        print('ERROR: Circular or unresolvable Reference in Dielectrics: ', unresolved_names)
        exit(1)

      remaining = still_remaining


  def calculate_zpositions (self):
    """dielectrics in XML are in reverse order, so we need to build position upside down.
       Resolves every dielectric's zmin/zmax via _assign_implicit_references() +
       resolve_references() - kept as one method (same name/signature as before Reference
       existed) since it's called from several places that don't need to know both steps happen.
    """
    self._assign_implicit_references()
    self.resolve_references()


  def get_by_name (self, name_to_find):  
    """find material object from materialname
    Args:
        name_to_find (string): name of material to find
    Returns:
        dielectric_layer: dielectric with that name, otherwise None
    """

    found = None
    for dielectric in self.dielectrics:
      if dielectric.name.upper() ==  name_to_find.upper():
        found = dielectric
    return found    


  def get_boundary_layers (self):
    """For substrates where Boundary is specified in dielectric layers, return a list of those layers. This is required for the next step, GDSII reader, which needs to know the layers to read. 
    Returns:
        list of int: list of layer numbers specified as boundary
    """
    
    boundary_layer_list = []
    for dielectric in self.dielectrics:
      if dielectric.gdsboundary is not None:
        value = int(dielectric.gdsboundary)
        if value not in boundary_layer_list:
          boundary_layer_list.append(value) 
    return boundary_layer_list
  

  def register_metals_inside (self, metals_list):
    """iterates over dielectrics and metals, sets metals_inside property for each dielectric
       with the list of metals that originate inside it - i.e. whichever single dielectric's
       [zmin, zmax) range contains the metal's own zmin, regardless of where its zmax ends
       up. A metal is deliberately not required to fit fully inside one dielectric: Reference
       positioning (or just an unusual absolute Zmin/Zmax) can legitimately push a metal's
       zmax past the dielectric it starts in and into the next one(s) above - it still needs
       to be registered exactly once (with the dielectric it starts in), not silently dropped
       everywhere. Membership by zmin alone also naturally covers a metal that exactly fills
       its dielectric's whole height (no separate exact-match case needed).

       _BOUNDARY_EPSILON shifts both comparisons inward by a tiny amount: a metal's zmin and
       a dielectric's zmin/zmax can both represent the exact same physical boundary point yet
       differ by float noise on the order of 1e-13 - one computed via cumulative Thickness
       summation down the dielectric stack, the other via a Layer's own Zmin plus a Substrate
       Offset, two unrelated accumulation paths. Comparing them with a bare "<"/">=" lets that
       noise decide, unpredictably, whether a boundary-sitting metal (zero actual overlap)
       gets misassigned to the dielectric below instead of the one above it actually starts
       in. 1e-6 (1 nanometre) is far larger than that noise and far smaller than any real
       stackup dimension in this schema (micron-scale), so it only ever affects true
       boundary coincidences, never a metal that's genuinely, non-trivially inside a
       dielectric.
    Args:
        metals_list (metal_layers_list): metals read from stackup
    """
    _BOUNDARY_EPSILON = 1e-6
    for dielectric in self.dielectrics:
      enclosed = []
      for metal in metals_list.metals:
        if (metal.zmin >= dielectric.zmin - _BOUNDARY_EPSILON) and (metal.zmin < dielectric.zmax - _BOUNDARY_EPSILON):
          enclosed.append(metal)
      dielectric.metals_inside = enclosed


# -------------------- conductor layers (metal and via) ---------------------------

class metal_layer:
  """
    drawing layer object ( name metal_layer is misleading, this drawn layer that uses material from the XML materials section)
  """
    
  def __init__ (self, data, variables=None):
    """create metal layer object (planar metal, via, sheet or dielectric) from XML data line

    Args:
        data (string): line from XML data, required parameters: "Name","Layer","Type","Material","Zmin","Zmax".
          Optional "Reference"/"ReferenceEdge": if "Reference" names another Dielectric or Layer, "Zmin"/"Zmax"
          are interpreted as offsets from that layer's edge instead of absolute z, resolved later by resolve().
        variables (variables_list, optional): fully-resolved <Variables>, for resolving any
          "="-prefixed expression among this layer's attributes. Defaults to an empty
          variables_list if omitted - see stackup_material.__init__ for why.
       """
    if variables is None:
      variables = variables_list()
    self.name = resolve_attr(data, "Name", None, variables)
    self.layernum = resolve_int_attr(data, "Layer", variables)
    self.type = resolve_attr(data, "Type", None, variables).upper()
    self.material = resolve_attr(data, "Material", None, variables)

    self.reference = resolve_attr(data, "Reference", None, variables) or None
    self.reference_edge = resolve_attr(data, "ReferenceEdge", "Top", variables)

    zmin_attr = resolve_attr(data, "Zmin", None, variables)
    zmax_attr = resolve_attr(data, "Zmax", None, variables)
    # force to sheet if zero thickness (resolved-value compare, same convention whether Zmin/Zmax are absolute or offsets)
    if zmin_attr == zmax_attr:
      self.type = "SHEET"

    self.is_used = False

    # Metals directly above and below, this is set by metal_layers_list.sort_and_evaluate()
    self.above = []
    self.below = []

    if self.reference:
      # Zmin/Zmax are offsets from the resolved Reference edge; actual zmin/zmax are set by resolve()
      self.offset_zmin = float(zmin_attr)
      self.offset_zmax = float(zmax_attr)
      self.zmin = None
      self.zmax = None
      self.resolved = False
    else:
      self.zmin = float(zmin_attr)
      self.zmax = float(zmax_attr)
      self.resolved = True
      self._finalize_type_flags()


  def _finalize_type_flags (self):
    """Set thickness and is_via/is_metal/is_dielectric/is_sheet from self.type, and check sheet consistency.
       Requires self.zmin/self.zmax to already be concrete floats. Called from __init__ directly for
       absolute-position layers, or from resolve() once a Reference-based layer's offsets are resolved.
    """
    if self.type == "SHEET" and not self.zmin==self.zmax:
      print('ERROR: Layer ', self.name, ' is defined as sheet layer, but zmax is different from zmin. This is not valid!')
      exit(1)

    self.thickness = self.zmax-self.zmin
    self.is_via = (self.type=="VIA")
    self.is_metal = (self.type=="CONDUCTOR")
    self.is_dielectric = (self.type=="DIELECTRIC")
    self.is_sheet = (self.type=="SHEET")


  def resolve (self, dielectrics_list, metals_list):
    """Resolve a Reference-based layer's zmin/zmax from an offset into an absolute z position.
       No-op if already resolved (including non-Reference layers, which are resolved in __init__).
    Args:
        dielectrics_list (dielectric_layers_list): dielectrics to search for a Reference match
        metals_list (metal_layers_list): metals to search for a Reference match
    """
    if self.resolved:
      return

    target_dielectric = dielectrics_list.get_by_name(self.reference)
    target_metal = metals_list.getbylayername(self.reference)

    if target_dielectric is not None and target_metal is not None:
      print('ERROR: Layer ', self.name, ' has Reference="', self.reference, '" which is ambiguous - matches both a Dielectric and a Layer')
      exit(1)
    if target_dielectric is None and target_metal is None:
      print('ERROR: Layer ', self.name, ' has Reference="', self.reference, '" which matches no Dielectric or Layer')
      exit(1)

    edge = (self.reference_edge or "Top").upper()
    if edge not in ("TOP", "BOTTOM"):
      print('ERROR: Layer ', self.name, ' has invalid ReferenceEdge="', self.reference_edge, '", must be Top or Bottom')
      exit(1)

    if target_dielectric is not None:
      base = target_dielectric.zmax if edge == "TOP" else target_dielectric.zmin
    else:
      if not target_metal.resolved:
        # defensive: caller (metal_layers_list.resolve_references) is expected to only call
        # resolve() once a Layer reference target is already resolved
        print('ERROR: Layer ', self.name, ' references Layer "', self.reference, '" which is not yet resolved')
        exit(1)
      base = target_metal.zmax if edge == "TOP" else target_metal.zmin

    self.zmin = base + self.offset_zmin
    self.zmax = base + self.offset_zmax
    self._finalize_type_flags()
    self.resolved = True


  def __str__ (self):
    """String representation of dielectric_layer, useful for debugging
    Returns:
        string: String representation of stackup_material
    """

    # convert list of layers above and below to layer names
    below_names = []
    for layer in self.below:
      below_names.append(layer.name)

    above_names = []
    for layer in self.above:
      above_names.append(layer.name)


    mystr = '      Metal Name=' + self.name + ' Layer=' + self.layernum  + \
            ' Type=' + self.type + ' Material=' + self.material + \
            ' Zmin=' +  str(self.zmin) + ' Zmax=' +  str(self.zmax) + \
            ' below=' + str(below_names) + ' above=' + str(above_names)
    
    return mystr
  



class metal_layers_list:
  """
    list of drawn layer objects (metal, via, dielectric brick)
  """


  def __init__ (self):
    """Initialize emptry list
    """
    self.metals = []      # list with conductor objects
    self.lowest = None    # metal with smallest zmin value
    self.orphan_layers = []  # list with layers that have no direct neighbor above or below
    self.derived_layers = derived_layers_list()  # empty by default, populated by read_substrate() if XML has a DerivedLayers section

  def append (self, metal):
    """Append one metal layer (drawn layer)
    Args:
        metal (metal_layer): metal layer to be added to list
    """
    self.metals.append (metal)

  
  def getbylayernumber (self, number_to_find):
    """Find metal layer by layer number, returns first match
    Args:
        number_to_find (int): layer number to find
    Returns:
        metal_layer: metal layer with that layer number
    """
    
    found = None
    for metal in self.metals:
      if metal.layernum == str(number_to_find):
        found = metal
        break 
    return found  


  def getallbylayernumber (self, number_to_find):
    """returns all metals by layer number as list, finds multiple metals mapped to same number
    Args:
        number_to_find (int): layer number to find
    Returns:
        list: list of metal_layer with that layer number, None if not found
    """
         
    found = []
    for metal in self.metals:
      if metal.layernum == str(number_to_find):
          found.append(metal)
    if found==[]:
      found = None
    return found  


  def getallplanarmetals (self):
    """returns all metals (conductor or sheet) as list, skip vias and dielectric vias
    Returns:
        list: list of metal_layer 
    """
         
    found = []
    for metal in self.metals:
      if metal.is_metal or metal.is_sheet:
          found.append(metal)
    return found  


  def getbylayername (self, name_to_find):
    """Find metal layer by layer number, returns first match
    Args:
        name_to_find (string): layer name to find
    Returns:
        metal_layer: metal layer with that layer name
    """

    found = None
    for metal in self.metals:
      if metal.name == str(name_to_find):
        found = metal
        break 
    return found  


  def getlayernumbers (self):
    """list of all metal and via layer numbers in technology
    Returns:
        list of int: all layer numbers in technology file
    """

    layernumbers = []
    for metal in self.metals:
      layernumbers.append(int(metal.layernum))
    return layernumbers 


  def has_references (self):
    """List of names of layers that use Reference-based (offset) positioning.
    Returns:
        list of string: names of layers where .reference is set
    """
    return [metal.name for metal in self.metals if metal.reference]


  def resolve_references (self, dielectrics_list):
    """Resolve all Reference-based layers' offsets into absolute zmin/zmax, in dependency order
       (a Layer can reference another Layer, which must be resolved first). Modeled on
       derived_layers_list.get_ordered(): repeat until no more progress can be made; any layers
       still unresolved at that point are part of a circular or unresolvable Reference chain.
    Args:
        dielectrics_list (dielectric_layers_list): dielectrics, used as possible Reference targets
    """
    remaining = [metal for metal in self.metals if not metal.resolved]

    while remaining:
      progress = False
      still_remaining = []

      for metal in remaining:
        target_dielectric = dielectrics_list.get_by_name(metal.reference)
        target_metal = self.getbylayername(metal.reference)
        # ready to resolve once the reference names a Dielectric (always resolvable), or a Layer
        # that is itself already resolved; an unresolvable/ambiguous name is also "ready" here so
        # that metal.resolve() reports the precise error immediately instead of stalling this loop
        if target_dielectric is not None or target_metal is None or target_metal.resolved:
          metal.resolve(dielectrics_list, self)
          progress = True
        else:
          still_remaining.append(metal)

      if not progress:
        unresolved_names = [metal.name for metal in still_remaining]
        print('ERROR: Circular or unresolvable Reference in Layers: ', unresolved_names)
        exit(1)

      remaining = still_remaining


  def add_offset (self, offset):
    """Add offset in z position to all metal layers, used to add stackup height for final z position
    Args:
        offset (float): z offset in project units
    """
    for metal in self.metals:
      metal.zmin = metal.zmin + offset
      metal.zmax = metal.zmax + offset


  def sort_and_evaluate(self):
    """After reading all metals, sort them by position and detect the neighbors above/below
       This is set in each metal as .above and .below list
    """
    # sort the list by zmin of each metal
    self.metals.sort(key=lambda metal: metal.zmin)
    # metal with lowest zmin value
    self.lowest = self.metals[0]
    self.highest = self.metals[-1]

    # delta for comparison, i.e. what is considered equal
    delta = 1e-5

    # Build above/below relationships efficiently
    for i, layer in enumerate(self.metals):
        # Layers above: all layers with zmin >= current zmax
        for other in self.metals[i+1:]:
            if abs(other.zmin - layer.zmax) < delta:
                layer.above.append(other)
        # Layers below: all layers with zmax <= current zmin
        for other in self.metals[:i]:
            if abs(other.zmax - layer.zmin) < delta:
                layer.below.append(other)

    # Identify orphan layers (no above or below)
    self.orphan_layers = [layer for layer in self.metals if not layer.above and not layer.below]


# -------------------- derived layers (boolean operations on other layers) ---------------------------

class derived_layer:
  """
    derived layer object, defines a new layer number that is computed via boolean operation
    on other layers (native GDSII layers or other derived layers), instead of being read
    directly from GDSII. Optionally, the result can be grown or shrunk by a fixed distance
    (Oversize). Operation "SIZE" takes a single operand and applies only the Oversize, with
    no boolean operation.
  """

  VALID_OPERATIONS = ("AND", "OR", "XOR", "NOT", "SIZE")

  def __init__ (self, data, variables=None):
    """create derived layer object from XML data line

    Args:
        data (xml.etree.ElementTree.Element): "DerivedLayer" XML element, required attributes
          "Name", "Layer", "Operation" ; optional attribute "Oversize" (grow outline by this
          distance in layout units, negative value shrinks); child "Operand" elements with
          "Layer" attribute, in order. For "NOT", first operand minus all following operands.
          Order does not matter for "AND", "OR", "XOR". "SIZE" takes exactly one operand and
          requires a non-zero Oversize; it just resizes that operand onto the new layer number.
        variables (variables_list, optional): fully-resolved <Variables>, for resolving any
          "="-prefixed expression among this derived layer's (and its Operands') attributes.
          Defaults to an empty variables_list if omitted - see stackup_material.__init__ for why.
    """
    if variables is None:
      variables = variables_list()
    self.name = resolve_attr(data, "Name", None, variables)
    self.layernum = resolve_int_attr(data, "Layer", variables)

    operation = resolve_attr(data, "Operation", None, variables)
    self.operation = operation.upper() if operation is not None else None
    if self.operation not in self.VALID_OPERATIONS:
      print('ERROR: Derived layer ', self.name, ' has invalid Operation "', operation, '". Must be one of ', self.VALID_OPERATIONS)
      exit(1)

    oversize = resolve_attr(data, "Oversize", None, variables)
    self.oversize = float(oversize) if oversize is not None else 0.0

    self.operands = []
    for operand in data.findall("Operand"):
      self.operands.append(resolve_int_attr(operand, "Layer", variables))

    if self.operation == "SIZE":
      if len(self.operands) != 1:
        print('ERROR: Derived layer ', self.name, ' has Operation="SIZE", which needs exactly 1 Operand entry, found ', len(self.operands))
        exit(1)
      if self.oversize == 0:
        print('ERROR: Derived layer ', self.name, ' has Operation="SIZE", which needs a non-zero Oversize value')
        exit(1)
    elif len(self.operands) < 2:
      print('ERROR: Derived layer ', self.name, ' needs at least 2 Operand entries, found ', len(self.operands))
      exit(1)


  def __str__ (self):
    """String representation of derived_layer, useful for debugging
    Returns:
        string: String representation of derived_layer
    """
    mystr = '      DerivedLayer Name=' + self.name + ' Layer=' + self.layernum + \
            ' Operation=' + self.operation + ' Operands=' + str(self.operands) + \
            ' Oversize=' + str(self.oversize)
    return mystr



class derived_layers_list:
  """
    list of derived layer objects. Operands of a derived layer can be native GDSII layers
    or other derived layers, so this class also provides dependency resolution (topological
    sort) to determine a safe processing order.
  """

  def __init__ (self):
    """Initialize empty list
    """
    self.derived_layers = []

  def append (self, derived):
    """Append one derived layer
    Args:
        derived (derived_layer): derived layer to add to list
    """
    self.derived_layers.append (derived)


  def getbylayernumber (self, number_to_find):
    """Find derived layer by layer number
    Args:
        number_to_find (int): layer number to find
    Returns:
        derived_layer: derived layer with that layer number, None if not found
    """
    found = None
    for derived in self.derived_layers:
      if derived.layernum == str(number_to_find):
        found = derived
        break
    return found


  def getlayernumbers (self):
    """list of all derived layer numbers
    Returns:
        list of int: all derived layer numbers
    """
    layernumbers = []
    for derived in self.derived_layers:
      layernumbers.append(int(derived.layernum))
    return layernumbers


  def get_ordered (self):
    """Resolve dependencies between derived layers (a derived layer can use another derived
       layer as operand) and return the list sorted so that a derived layer never appears
       before the derived layers it depends on. Native GDSII layer operands are not
       dependencies here, since they need no prior computation.
    Returns:
        list of derived_layer: topologically sorted derived layers
    Raises:
        SystemExit: if a circular or otherwise unresolvable dependency is detected
    """

    resolved = []
    resolved_layernums = set()
    remaining = list(self.derived_layers)

    while remaining:
      progress = False
      still_remaining = []

      for derived in remaining:
        # dependencies are operands that are themselves derived layers (not native GDSII layers)
        dependencies = [op for op in derived.operands if self.getbylayernumber(op) is not None]
        if all(dep in resolved_layernums for dep in dependencies):
          resolved.append(derived)
          resolved_layernums.add(derived.layernum)
          progress = True
        else:
          still_remaining.append(derived)

      if not progress:
        unresolved_names = [derived.name for derived in still_remaining]
        print('ERROR: Circular or unresolved dependency in DerivedLayers: ', unresolved_names)
        exit(1)

      remaining = still_remaining

    return resolved


# ----------- thermal tables -----------------

class thermal_table:
    def __init__(self, xml_data, variables=None):
        if variables is None:
            variables = variables_list()
        self.name = resolve_attr(xml_data, "Name", None, variables)
        self.points = []

        for point in xml_data.iter("Point"):
            T = float(resolve_attr(point, "Temperature", None, variables))
            k = float(resolve_attr(point, "Value", None, variables))
            self.points.append((T, k))


class thermal_tables_list(list):
    def get(self, name):
        for table in self:
            if table.name == name:
                return table
        return None


# ----------- parse substrate file, get materials from list created before -----------

GENERATOR_COMMENT_PREFIX = "Created/modified using the XML Stackup Editor in"
DESCRIPTION_COMMENT_PREFIX = "File description:"
_HEADER_SEPARATOR_TEXT = "=" * 60
# duplicated (not imported) from util_stackup_writer.py deliberately: that module
# is specific to the interactive XML editor, while this reader module is used by
# the whole gds2palace pipeline and is meant to stay independent of it. Two formats
# are recognized: the current one (generator stamp, separator, one comment per
# description line with nothing prepended, closing separator) and the older one
# (generator stamp, separator, a single comment prefixed with
# DESCRIPTION_COMMENT_PREFIX holding the whole possibly-multi-line description) that
# util_stackup_writer.py itself still reads for backward compatibility with files
# saved before the format changed.


def read_file_description (XML_filename):
  """
  Read the free-text file description previously stamped by the XML Stackup Editor
  (see util_stackup_writer.stamp_header_comments), if any. Cheap standalone lookup
  that does not build the full materials/dielectrics/metals object model.
  Args:
      XML_filename (string): filename of XML technology file
  Returns:
      string: the description text, or "" if the file has none / is missing / fails to parse
  """
  if not XML_filename or not os.path.isfile(XML_filename):
    return ""

  try:
    root = xml.etree.ElementTree.parse(XML_filename, parser=_make_comment_preserving_parser()).getroot()
  except xml.etree.ElementTree.ParseError:
    return ""

  children = list(root)
  if (len(children) >= 2
      and children[0].tag is xml.etree.ElementTree.Comment
      and (children[0].text or "").strip().startswith(GENERATOR_COMMENT_PREFIX)
      and children[1].tag is xml.etree.ElementTree.Comment
      and (children[1].text or "").strip() == _HEADER_SEPARATOR_TEXT):
    lines = []
    for child in children[2:]:
      if child.tag is not xml.etree.ElementTree.Comment:
        break
      text = (child.text or "").strip()
      if text == _HEADER_SEPARATOR_TEXT:
        return "\n".join(lines)
      lines.append(text)
    # no closing separator found - not a well-formed current-format block, fall
    # through to the legacy single-comment lookup below

  for child in root:
    if child.tag is xml.etree.ElementTree.Comment:
      text = (child.text or "").strip()
      if text.startswith(DESCRIPTION_COMMENT_PREFIX):
        return text[len(DESCRIPTION_COMMENT_PREFIX):].strip()
  return ""


def read_substrate (XML_filename, variable_overrides=None):
  """
  Read XML substrate and return materials_list, dielectrics_list, metals_list.
  Derived layer definitions (if any) are attached as metals_list.derived_layers,
  so this return signature stays backward compatible with existing 3-value unpacking.
  Args:
      XML_filename (string): filename of XML technology file
      variable_overrides (dict, optional): variable name -> plain override value
        (float/int/str), applied to this file's <Variables> before anything else is resolved -
        e.g. from a parametric sweep script. See variables_list.apply_overrides(). None (the
        default) applies no overrides, leaving every variable exactly as the XML declares it.
  """

  if os.path.isfile(XML_filename):
    # print('Reading XML stackup  file:', XML_filename)

    # data source is *.subst XML file; comment-preserving parser so that callers who
    # keep the parsed tree around for editing (e.g. a GUI editor) don't lose comments
    substrate_tree = xml.etree.ElementTree.parse(XML_filename, parser=_make_comment_preserving_parser())
    substrate_root = substrate_tree.getroot()

    # checked here (once per file load) rather than inside parse_substrate() itself, which
    # is also called repeatedly for in-memory live-preview re-derivation (e.g. by a GUI
    # editor on every edit) - that would otherwise reprint the same warning constantly
    check_schema_version(substrate_root)

    return parse_substrate(substrate_root, variable_overrides)

  else:
    print('XML stackup file not found: ', XML_filename)
    exit(1)


def parse_substrate (substrate_root, variable_overrides=None):
  """
  Build materials_list, dielectrics_list, metals_list from an already-parsed XML
  <Stackup> root element. This is the part of read_substrate() that doesn't touch
  disk, split out so callers that already hold a parsed/edited tree in memory (e.g.
  a GUI editor re-deriving a live preview after an edit) can re-run it without a
  round trip through the filesystem.
  Args:
      substrate_root (xml.etree.ElementTree.Element): root element of a stackup XML tree
      variable_overrides (dict, optional): see read_substrate()
  """

  # get variables from XML first (if present) - every other attribute in the file may
  # reference one via a "="-prefixed expression, so these must be fully resolved before
  # anything else below is parsed. Overrides are applied before resolve_all() so dependency
  # resolution sees them from the start - an overridden variable is marked resolved
  # immediately, so any formula variable built on top of it (overridden or not) picks up the
  # override value in the same single resolution pass.
  variables = variables_list()
  for data in substrate_root.iter("Variable"):
      variables.append (variable(data))
  variables.apply_overrides(variable_overrides)
  variables.resolve_all()

  # get materials  from  XML
  materials_list = stackup_materials_list() # initialize empty list
  for data in  substrate_root.iter("Material"):
      materials_list.append (stackup_material(data, variables))

  # get dielectric layers from  XML
  dielectrics_list = dielectric_layers_list() # initialize empty list
  for data in  substrate_root.iter("Dielectric"):
      dielectrics_list.append (dielectric_layer(data, variables), materials_list)

  # get optional thermal tables from XML
  thermal_tables = thermal_tables_list()
  tables = substrate_root.find("Tables")
  if tables is not None:
      for data in tables.findall("Table"):
          thermal_tables.append(thermal_table(data, variables))

  # iterate over materials to check if they refer to a thermal table
  for material in materials_list.materials:
    if material.thermaltablename != "":
      material.thermaltable = thermal_tables.get(material.thermaltablename)
    else:
      material.thermaltable = None

  # calculate z positions in dielectric layers, after reading all of them
  dielectrics_list.calculate_zpositions()

  # mark top and bottom, order from XML is top material first
  if len(dielectrics_list.dielectrics) > 0:
    zmin_overall = math.inf
    zmax_overall = -math.inf
    lowest = None
    highest = None

    for dielectric in dielectrics_list.dielectrics:
      if dielectric.zmin < zmin_overall:
        zmin_overall = dielectric.zmin
        lowest = dielectric
      if dielectric.zmax > zmax_overall:
        zmax_overall = dielectric.zmax
        highest = dielectric

    if highest is not None:
      highest.is_top = True
    if lowest is not None:
      lowest.is_bottom = True

  # get metal layers (metals + vias) from XML
  metals_list = metal_layers_list() # initialize empty list
  for data in  substrate_root.iter("Layer"):
      metals_list.append (metal_layer(data, variables))

  # resolve Reference-based layers (offsets from a Dielectric or another Layer edge) into absolute zmin/zmax
  metals_list.resolve_references(dielectrics_list)

  # sort metals by zmin and detect their neighbors above/below
  metals_list.sort_and_evaluate()

  # get derived layers (boolean operations on other layers) from XML, if present
  # attached to metals_list instead of added as a new return value, so that existing
  # code doing "materials_list, dielectrics_list, metals_list = read_substrate(...)" keeps working
  derived_layers_section = substrate_root.find(".//DerivedLayers")
  if derived_layers_section is not None:
    for data in derived_layers_section.findall("DerivedLayer"):
      metals_list.derived_layers.append (derived_layer(data, variables))

  # get substrate offset, required for v2 stackup file version
  offset = 0
  for data in substrate_root.iter("Substrate"):
      assert data!=None
      offset = float(resolve_attr(data, "Offset", 0, variables))
  if offset > 0:
    referenced_layers = metals_list.has_references()
    if referenced_layers:
      print('ERROR: <Substrate Offset="..."> cannot be combined with Reference-based Layer positioning. Layers using Reference: ', referenced_layers)
      exit(1)
    metals_list.add_offset(offset)

  # register metals with the enclosing dielectrics
  dielectrics_list.register_metals_inside (metals_list)

  return materials_list, dielectrics_list, metals_list


# =======================================================================================
# Test code when running as standalone script
# =======================================================================================

if __name__ == "__main__":

  XML_filename = "SG13G2_200um.xml"
  materials_list, dielectrics_list, metals_list = read_substrate (XML_filename)
  derived_layers = metals_list.derived_layers

  for material in materials_list.materials:
    print(material)

  for dielectric in dielectrics_list.dielectrics:
    print(dielectric)

  for metal in metals_list.metals:
    print(metal)

  print('__________________________________________')

  # test finding a layer by layer number
  metal = metals_list.getbylayernumber (134)
  print('Layer 134 name => ', metal.name)

  print('Layer 134 thickness => ', metals_list.getbylayernumber (134).thickness)
  print('Test if Layer 134 is a via layer => ', metals_list.getbylayernumber(134).is_via)

  # test finding a layer by name
  metal = metals_list.getbylayername ("TopMetal1")
  print('TopMetal1 layer number => ', metal.layernum)

  # find orphaned layers that have no neighbor above or below
  orphan_names = []
  for layer in metals_list.orphan_layers:
    orphan_names.append(layer.name)
  print('Orphaned layers: ', orphan_names)  

  # get all planar metals in stackup (no via, no dielectric via)
  planar_metal_names = []
  for metal in metals_list.getallplanarmetals():
    planar_metal_names.append(metal.name)
  print('Planar metals: ', planar_metal_names)  

  # get all planar metals inside a dielectric
  DK = dielectrics_list.get_by_name('SiO2')
  if DK is not None:
    names = []
    metals = DK.get_planar_metals_inside()
    for metal in metals:
      names.append(metal.name)
    print('Planar metals inside ', DK.name, ': ', names)

  print('__________________________________________')

  for derived in derived_layers.derived_layers:
    print(derived)

  # test finding a derived layer by layer number
  derived = derived_layers.getbylayernumber (240)
  if derived is not None:
    print('Layer 240 name => ', derived.name)
    print('Layer 240 operation => ', derived.operation)
    print('Layer 240 operands => ', derived.operands)

  # dependency-resolved processing order (derived layers built from other derived layers come last)
  processing_order = [derived.name for derived in derived_layers.get_ordered()]
  print('Derived layer processing order: ', processing_order)

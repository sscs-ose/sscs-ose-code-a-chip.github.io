if not set -q PERFPDN_PDK_ROOT; or test -z "$PERFPDN_PDK_ROOT"
    set -g PERFPDN_PDK_ROOT "$HOME/.local/share/perfpdn/pdks"
end
set -gx PERFPDN_PDK_ROOT "$PERFPDN_PDK_ROOT"
set -gx PDK_ROOT "$PERFPDN_PDK_ROOT"
set -gx PDK sky130A

// $Id: CglCutGenerator.cpp 1442 2019-01-06 16:39:41Z unxusr $
// Copyright (C) 2000, International Business Machines
// Corporation and others.  All Rights Reserved.
// This code is licensed under the terms of the Eclipse Public License (EPL).

#include <cstdlib>
#include <cassert>
//#include <cfloat>
//#include <iostream>

#include "CoinPragma.hpp"
#include "CglCutGenerator.hpp"
#include "CoinHelperFunctions.hpp"

//-------------------------------------------------------------------
// Default Constructor
//-------------------------------------------------------------------
CglCutGenerator::CglCutGenerator()
  : aggressive_(0)
  , canDoGlobalCuts_(false)
{
  // nothing to do here
}

//-------------------------------------------------------------------
// Copy constructor
//-------------------------------------------------------------------
CglCutGenerator::CglCutGenerator(
  const CglCutGenerator &source)
  : aggressive_(source.aggressive_)
  , canDoGlobalCuts_(source.canDoGlobalCuts_)
{
  // nothing to do here
}

//-------------------------------------------------------------------
// Destructor
//-------------------------------------------------------------------
CglCutGenerator::~CglCutGenerator()
{
  // nothing to do here
}

//----------------------------------------------------------------
// Assignment operator
//-------------------------------------------------------------------
CglCutGenerator &
CglCutGenerator::operator=(
  const CglCutGenerator &rhs)
{
  if (this != &rhs) {
    aggressive_ = rhs.aggressive_;
    canDoGlobalCuts_ = rhs.canDoGlobalCuts_;
  }
  return *this;
}
bool CglCutGenerator::mayGenerateRowCutsInTree() const
{
  return true;
}
// Return true if needs optimal basis to do cuts
bool CglCutGenerator::needsOptimalBasis() const
{
  return false;
}

#ifdef NDEBUG
#undef NDEBUG
#endif

#if 0
//--------------------------------------------------------------------------
// test EKKsolution methods.
//--------------------------------------------------------------------------
void
CglCutGenerator::unitTest()
{
}
#endif

/* vi: softtabstop=2 shiftwidth=2 expandtab tabstop=2
*/

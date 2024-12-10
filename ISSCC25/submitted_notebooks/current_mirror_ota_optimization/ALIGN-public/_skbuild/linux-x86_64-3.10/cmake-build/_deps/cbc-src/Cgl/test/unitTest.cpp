// $Id: unitTest.cpp 1114 2013-04-06 14:00:12Z stefan $
// Copyright (C) 2000, International Business Machines
// Corporation and others.  All Rights Reserved.
// This code is licensed under the terms of the Eclipse Public License (EPL).

// Test individual classes or groups of classes

#include "CoinPragma.hpp"

#include "CglConfig.h"

#include <string>
#include <cstring>
#include <cassert>
#include <iostream>
#include <cstdlib>

#ifdef COIN_HAS_OSICPX
#include <OsiCpxSolverInterface.hpp>
#endif
#ifdef COIN_HAS_OSIXPR
#include <OsiXprSolverInterface.hpp>
#endif
#ifdef COIN_HAS_OSICLP
#include <OsiClpSolverInterface.hpp>
#endif
#ifdef COIN_HAS_OSIDYLP
#include <OsiDylpSolverInterface.hpp>
#endif
#ifdef COIN_HAS_OSIGLPK
#include <OsiGlpkSolverInterface.hpp>
#endif
#ifdef COIN_HAS_OSIVOL
#include <OsiVolSolverInterface.hpp>
#endif

#include "CglSimpleRounding.hpp"
#include "CglKnapsackCover.hpp"
#include "CglOddHole.hpp"
#include "CglProbing.hpp"
#include "CglGomory.hpp"
#include "CglLandP.hpp"
#include "CglMixedIntegerRounding.hpp"
#include "CglMixedIntegerRounding2.hpp"
#include "CglResidualCapacity.hpp"
#include "CglRedSplit.hpp"
#include "CglRedSplit2.hpp"
#include "CglTwomir.hpp"
#include "CglClique.hpp"
#include "CglFlowCover.hpp"
#include "CglZeroHalf.hpp"

// Function Prototypes. Function definitions is in this file.
void testingMessage( const char * const msg );

// Command line parameters are directories containing data files.
// You must specify both mpsDir and testDir, in order.
// If not specified, then "../../Data/Sample/" and
// "CglTestData/" are used

int main (int argc, const char *argv[])
{
  // Initialize directories containing data files.
  std::string mpsDir;
  std::string testDir;
  
  const char dirsep =  CoinFindDirSeparator();
  if (dirsep == '/') {
#ifdef SAMPLEDIR
    mpsDir = SAMPLEDIR "/" ;
#else
    mpsDir = "../../Data/Sample/";
#endif
#ifdef TESTDIR
    testDir = TESTDIR "/" ;
#else
    testDir = "CglTestData/";
#endif
  } else {
#ifdef SAMPLEDIR
    mpsDir = SAMPLEDIR "\\" ;
#else
    mpsDir = "..\\..\\Data\\Sample\\";
#endif
#ifdef TESTDIR
    testDir = TESTDIR "\\";
#else
    testDir = "CglTestData\\";
#endif
  }
  // Check for command line override
  if (argc >= 2) {
    mpsDir = argv[1];
    mpsDir += dirsep;
    if (argc >= 3) {
      testDir = argv[2];
      testDir += dirsep;
    }
  }

#ifdef COIN_HAS_OSICPX
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglGomory with OsiCpxSolverInterface\n" );
    CglGomoryUnitTest(&cpxSi,mpsDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglSimpleRounding with OsiCpxSolverInterface\n" );
    CglSimpleRoundingUnitTest(&cpxSi,mpsDir);
  }
  if(0) // Test does not work with Cplex
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglKnapsackCover with OsiCpxSolverInterface\n" );
    CglKnapsackCoverUnitTest(&cpxSi,mpsDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglOddHole with OsiCpxSolverInterface\n" );
    CglOddHoleUnitTest(&cpxSi,mpsDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglProbing with OsiCpxSolverInterface\n" );
    CglProbingUnitTest(&cpxSi,mpsDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglMixedIntegerRounding with OsiCpxSolverInterface\n" );
    CglMixedIntegerRoundingUnitTest(&cpxSi, testDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglMixedIntegerRounding2 with OsiCpxSolverInterface\n" );
    CglMixedIntegerRounding2UnitTest(&cpxSi, testDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglResidualCapacity with OsiCpxSolverInterface\n" );
    CglResidualCapacityUnitTest(&cpxSi, testDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglRedSplit with OsiCpxSolverInterface\n" );
    CglRedSplitUnitTest(&cpxSi, mpsDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglTwomir with OsiCpxSolverInterface\n" );
    CglTwomirUnitTest(&cpxSi, testDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglClique with OsiCpxSolverInterface\n" );
    CglCliqueUnitTest(&cpxSi, testDir);
  }
  {
    OsiCpxSolverInterface cpxSi;
    testingMessage( "Testing CglFlowCover with OsiCpxSolverInterface\n" );
    CglFlowCoverUnitTest(&cpxSi, testDir);
  }

#endif

#ifdef COIN_HAS_OSIXPR
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglGomory with OsiXprSolverInterface\n" );
    CglGomoryUnitTest(&xprSi,mpsDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglSimpleRounding with OsiXprSolverInterface\n" );
    CglSimpleRoundingUnitTest(&xprSi,mpsDir);
  }
  if(0) 
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglKnapsackCover with OsiXprSolverInterface\n" );
    CglKnapsackCoverUnitTest(&xprSi,mpsDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglOddHole with OsiXprSolverInterface\n" );
    CglOddHoleUnitTest(&xprSi,mpsDir);
  }
  if(0)     // Does not work with Xpress
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglProbing with OsiXprSolverInterface\n" );
    CglProbingUnitTest(&xprSi,mpsDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglMixedIntegerRounding with OsiXprSolverInterface\n" );
    CglMixedIntegerRoundingUnitTest(&xprSi, testDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglMixedIntegerRounding2 with OsiXprSolverInterface\n" );
    CglMixedIntegerRounding2UnitTest(&xprSi, testDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglResidualCapacity with OsiXprSolverInterface\n" );
    CglResidualCapacityUnitTest(&xprSi, testDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglTwomir with OsiXprSolverInterface\n" );
    CglTwomirUnitTest(&xprSi, testDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglClique with OsiXprSolverInterface\n" );
    CglCliqueUnitTest(&xprSi, testDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglFlowCover with OsiXprSolverInterface\n" );
    CglFlowCoverUnitTest(&xprSi, testDir);
  }
  {
    OsiXprSolverInterface xprSi;
    testingMessage( "Testing CglZeroHalf with OsiXprSolverInterface\n" );
    CglZeroHalfUnitTest(&xprSi, testDir);
  }

#endif
#ifdef COIN_HAS_OSICLP
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglGomory with OsiClpSolverInterface\n" );
    CglGomoryUnitTest(&clpSi,mpsDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglLandp with OsiClpSolverInterface\n" );
    CglLandPUnitTest(&clpSi,mpsDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglSimpleRounding with OsiClpSolverInterface\n" );
    CglSimpleRoundingUnitTest(&clpSi,mpsDir);
  }
  if (0) {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglKnapsackCover with OsiClpSolverInterface\n" );
    CglKnapsackCoverUnitTest(&clpSi,mpsDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglOddHole with OsiClpSolverInterface\n" );
    CglOddHoleUnitTest(&clpSi,mpsDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglProbing with OsiClpSolverInterface\n" );
    CglProbingUnitTest(&clpSi,mpsDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglMixedIntegerRounding with OsiClpSolverInterface\n" );
    CglMixedIntegerRoundingUnitTest(&clpSi, testDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglMixedIntegerRounding2 with OsiClpSolverInterface\n" );
    CglMixedIntegerRounding2UnitTest(&clpSi, testDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglResidualCapacity with OsiClpSolverInterface\n" );
    CglResidualCapacityUnitTest(&clpSi, testDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglRedSplit with OsiClpSolverInterface\n" );
    CglRedSplitUnitTest(&clpSi, mpsDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglRedSplit2 with OsiClpSolverInterface\n" );
    CglRedSplit2UnitTest(&clpSi, mpsDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglTwomir with OsiClpSolverInterface\n" );
    CglTwomirUnitTest(&clpSi, testDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglClique with OsiClpSolverInterface\n" );
    CglCliqueUnitTest(&clpSi, testDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglFlowCover with OsiClpSolverInterface\n" );
    CglFlowCoverUnitTest(&clpSi, testDir);
  }
  {
    OsiClpSolverInterface clpSi;
    testingMessage( "Testing CglZeroHalf with OsiClpSolverInterface\n" );
    CglZeroHalfUnitTest(&clpSi, testDir);
  }

#endif
#ifdef COIN_HAS_OSIDYLP
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglGomory with OsiDylpSolverInterface\n" );
    CglGomoryUnitTest(&dylpSi,mpsDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglSimpleRounding with OsiDylpSolverInterface\n" );
    CglSimpleRoundingUnitTest(&dylpSi,mpsDir);
  }
  if (0) {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglKnapsackCover with OsiDylpSolverInterface\n" );
    CglKnapsackCoverUnitTest(&dylpSi,mpsDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglOddHole with OsiDylpSolverInterface\n" );
    CglOddHoleUnitTest(&dylpSi,mpsDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglProbing with OsiDylpSolverInterface\n" );
    CglProbingUnitTest(&dylpSi,mpsDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglMixedIntegerRounding with OsiDylpSolverInterface\n" );
    CglMixedIntegerRoundingUnitTest(&dylpSi, testDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglMixedIntegerRounding2 with OsiDylpSolverInterface\n" );
    CglMixedIntegerRounding2UnitTest(&dylpSi, testDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglResidualCapacity with OsiDylpSolverInterface\n" );
    CglResidualCapacityUnitTest(&dylpSi, testDir);
  }
  if (0)  // needs partial OsiSimplex
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglRedSplit with OsiDylpSolverInterface\n" );
    CglRedSplitUnitTest(&dylpSi, mpsDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglTwomir with OsiDylpSolverInterface\n" );
    CglTwomirUnitTest(&dylpSi, testDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglClique with OsiDylpSolverInterface\n" );
    CglCliqueUnitTest(&dylpSi, testDir);
  }
  {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglFlowCover with OsiDylpSolverInterface\n" );
    CglFlowCoverUnitTest(&dylpSi, testDir);
  }
  if (0) {
    OsiDylpSolverInterface dylpSi;
    testingMessage( "Testing CglZeroHalf with OsiDylpSolverInterface\n" );
    CglZeroHalfUnitTest(&dylpSi, testDir);
  }

#endif
#ifdef COIN_HAS_OSIGLPK
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglGomory with OsiGlpkSolverInterface\n" );
    CglGomoryUnitTest(&glpkSi,mpsDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglSimpleRounding with OsiGlpkSolverInterface\n" );
    CglSimpleRoundingUnitTest(&glpkSi,mpsDir);
  }
  if (0) {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglKnapsackCover with OsiGlpkSolverInterface\n" );
    CglKnapsackCoverUnitTest(&glpkSi,mpsDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglOddHole with OsiGlpkSolverInterface\n" );
    CglOddHoleUnitTest(&glpkSi,mpsDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglProbing with OsiGlpkSolverInterface\n" );
    CglProbingUnitTest(&glpkSi,mpsDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglMixedIntegerRounding with OsiGlpkSolverInterface\n" );
    CglMixedIntegerRoundingUnitTest(&glpkSi, testDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglMixedIntegerRounding2 with OsiGlpkSolverInterface\n" );
    CglMixedIntegerRounding2UnitTest(&glpkSi, testDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglResidualCapacity with OsiGlpkSolverInterface\n" );
    CglResidualCapacityUnitTest(&glpkSi, testDir);
  }
  if (0)  // needs partial OsiSimplex
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglRedSplit with OsiGlpkSolverInterface\n" );
    CglRedSplitUnitTest(&glpkSi, mpsDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglTwomir with OsiGlpkSolverInterface\n" );
    CglTwomirUnitTest(&glpkSi, testDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglClique with OsiGlpkSolverInterface\n" );
    CglCliqueUnitTest(&glpkSi, testDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglFlowCover with OsiGlpkSolverInterface\n" );
    CglFlowCoverUnitTest(&glpkSi, testDir);
  }
  {
    OsiGlpkSolverInterface glpkSi;
    testingMessage( "Testing CglZeroHalf with OsiGlpkSolverInterface\n" );
    CglZeroHalfUnitTest(&glpkSi, testDir);
  }

#endif

#ifdef COIN_HAS_OSIVOL
  if(0) // p0033: LP not solved to optimality: Finds 2142 versus 2520
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglGomory with OsiVolSolverInterface\n" );
    CglGomoryUnitTest(&volSi,mpsDir);
  }
  if(0) // Not expected number of cuts; might come from different solution?
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglSimpleRounding with OsiVolSolverInterface\n" );
    CglSimpleRoundingUnitTest(&volSi,mpsDir);
  }
  if(0) // tp3: LP not solved to optimality: Finds 97.1842 versus 97.185
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglKnapsackCover with OsiVolSolverInterface\n" );
    CglKnapsackCoverUnitTest(&volSi,mpsDir);
  }
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglOddHole with OsiVolSolverInterface\n" );
    CglOddHoleUnitTest(&volSi,mpsDir);
  }
  if(0) // Not expected number of elements in cut; might come from different solution?
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglProbing with OsiVolSolverInterface\n" );
    CglProbingUnitTest(&volSi,mpsDir);
  }
  if(0) // Throw CoinError since solver can not handle infinite bounds
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglMixedIntegerRounding with OsiVolSolverInterface\n" );
    CglMixedIntegerRoundingUnitTest(&volSi, testDir);
  }
  if(0) // Throw CoinError since solver can not handle infinite bounds
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglMixedIntegerRounding2 with OsiVolSolverInterface\n" );
    CglMixedIntegerRounding2UnitTest(&volSi, testDir);
  }
  if(0) // Throw CoinError since solver can not handle infinite bounds
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglResidualCapacity with OsiVolSolverInterface\n" );
    CglResidualCapacityUnitTest(&volSi, testDir);
  }
  if(0) // Throw CoinError since solver can not handle infinite bounds
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglTwomir with OsiVolSolverInterface\n" );
    CglTwomirUnitTest(&volSi, testDir);
  }
  if(0) // No cuts found
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglClique with OsiVolSolverInterface\n" );
    CglCliqueUnitTest(&volSi, testDir);
  }
  if(0) // Throw CoinError since solver can not handle infinite bounds
  {
    OsiVolSolverInterface volSi;
    testingMessage( "Testing CglFlowCover with OsiVolSolverInterface\n" );
    CglFlowCoverUnitTest(&volSi, testDir);
  }

#endif

  testingMessage( "All tests completed successfully\n" );
  return 0;
}

 
// Display message on stdout and stderr
void testingMessage( const char * const msg )
{
  std::cout <<std::endl <<"*****************************************"
            <<std::endl <<msg <<std::endl;
  //std::cerr <<msg;
}


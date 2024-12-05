/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* (c) Copyright 2006-2019 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include "CoinPragma.hpp"
#include "CoinHelperFunctions.hpp"
#include "SymConfig.h"

#include <iostream>

#ifdef _OPENMP
#include "omp.h"
#endif

#ifdef COIN_HAS_OSITESTS
#include "OsiUnitTests.hpp"
#include "OsiSolverInterface.hpp"
#include "OsiSymSolverInterface.hpp"

using namespace OsiUnitTest;

#else
#include <cstring>

void testingMessage( const char * const msg ) {
  std::cout.flush() ;
  std::cerr << msg;
}

#endif

#include "symphony.h"

int main (int argc, const char *argv[])
{
#ifdef _OPENMP
   omp_set_dynamic(FALSE);
   omp_set_num_threads(1);
#endif

  std::string miplib3Dir;
  /*
    Start off with various bits of initialisation that don't really belong
    anywhere else.

    Synchronise C++ stream i/o with C stdio. This makes debugging
    output a bit more comprehensible. It still suffers from interleave of cout
    (stdout) and cerr (stderr), but -nobuf deals with that.
  */
  std::ios::sync_with_stdio() ;
  /*
    Suppress an popup window that Windows shows in response to a crash. See
    note at head of file.
  */
  WindowsErrorPopupBlocker();

#ifdef COIN_HAS_OSITESTS
  /*
    Process command line parameters.
  */
  std::map<std::string,std::string> parms;
  if (processParameters(argc,argv,parms) == false)
  { return 1; }

  std::string mpsDir = parms["-mpsDir"] ;
  std::string netlibDir = parms["-netlibDir"] ;
  miplib3Dir = parms["-miplib3Dir"];

  /*
    Test Osi{Row,Col}Cut routines.
   */
  {
    OsiSymSolverInterface symSi;
    symSi.setSymParam(OsiSymVerbosity, -1);
    testingMessage( "Now testing the OsiRowCut class with OsiSymSolverInterface\n\n");
    OSIUNITTEST_CATCH_ERROR(OsiRowCutUnitTest(&symSi,mpsDir), {}, "symphony", "rowcut unittest");
  }
  {
    OsiSymSolverInterface symSi;
    symSi.setSymParam(OsiSymVerbosity, -1);
    testingMessage( "Now testing the OsiColCut class with OsiSymSolverInterface\n\n" );
    OSIUNITTEST_CATCH_ERROR(OsiColCutUnitTest(&symSi,mpsDir), {}, "symphony", "colcut unittest");
  }
  {
    OsiSymSolverInterface symSi;
    symSi.setSymParam(OsiSymVerbosity, -1);
    testingMessage( "Now testing the OsiRowCutDebugger class with OsiSymSolverInterface\n\n" );
    OSIUNITTEST_CATCH_ERROR(OsiRowCutDebuggerUnitTest(&symSi,mpsDir), {}, "symphony", "rowcut debugger unittest");
  }

  /*
    Run the OsiSym class test. This will also call OsiSolverInterfaceCommonUnitTest.
   */
  testingMessage( "Now testing OsiSymSolverInterface\n\n" );
  OSIUNITTEST_CATCH_ERROR(OsiSymSolverInterfaceUnitTest(mpsDir,netlibDir), {}, "symphony", "Osi unittest");

  /*
    We have run the specialised unit test.
    Check now to see if we need to run through the Netlib problems.
   */
  if (parms.find("-testOsiSolverInterface") != parms.end())
  {
    // Create vector of solver interfaces
    OsiSymSolverInterface* symSi = new OsiSymSolverInterface();
    symSi->setSymParam(OsiSymVerbosity, -1);
    std::vector<OsiSolverInterface*> vecSi(1, symSi);

    testingMessage( "Testing OsiSolverInterface on Netlib problems.\n" );
    OSIUNITTEST_CATCH_ERROR(OsiSolverInterfaceMpsUnitTest(vecSi,netlibDir), {}, "symphony", "Netlib unittest");

    delete vecSi[0];
  }
  else
  {
    testingMessage( "***Skipped Testing of OsiSymSolverInterface on Netlib problems, use -testOsiSolverInterface to run them.***\n" );
  }
#else
  /* a very light version of "parameter processing": check if user call with -miplib3Dir=<dir> */
  if( argc >= 2 && strncmp(argv[1], "-miplib3Dir", 11) == 0 )
    miplib3Dir = argv[1]+12;
#endif

  if (miplib3Dir.length() > 0) {
    int test_status;
    int symargc;
    char* symargv[7];
    testingMessage( "Testing MIPLIB files\n" );

    sym_environment *env = sym_open_environment();
    /* assemble arguments for symphony: -T miplibdir, and -p 2 if we run the punittest */
    symargc = 5;
    symargv[0] = CoinStrdup(argv[0]);
    symargv[1] = "-T";
    symargv[2] = CoinStrdup(miplib3Dir.c_str());
    if( argv[0][0] == 'p' || argv[0][0] == 'P' ) {
       symargv[3] = "-p";
       symargv[4] = "2";
    }else{
       symargv[3] = "-p";
       symargv[4] = "0";
    }
    //sym_parse_command_line(env, symargc, const_cast<char**>(symargv));
    sym_set_int_param(env, "verbosity", -10);
    sym_test(env, symargc, symargv, &test_status);

#ifdef COIN_HAS_OSITESTS
    OSIUNITTEST_ASSERT_WARNING(test_status == 0, {}, "symphony", "testing MIPLIB");
#else
    if (test_status > 0)
      testingMessage( "Warning: some instances may not have returned a correct solution\n");
#endif
  }

  /*
    We're done. Report on the results.
  */
#ifdef COIN_HAS_OSITESTS
  std::cout.flush();
  outcomes.print();

  int nerrors;
  int nerrors_expected;
  outcomes.getCountBySeverity(TestOutcome::ERROR, nerrors, nerrors_expected);

  if (nerrors > nerrors_expected)
    std::cerr << "Tests completed with " << nerrors - nerrors_expected << " unexpected errors." << std::endl ;
  else
    std::cerr << "All tests completed successfully\n";

  return nerrors - nerrors_expected;
#else

  testingMessage( "All tests completed successfully\n" );

  return 0;
#endif
}

// Copyright (C) 2000, International Business Machines
// Corporation and others.  All Rights Reserved.
// This code is licensed under the terms of the Eclipse Public License (EPL).

//----------------------------------------------------- 
// Simple example usage of the cut generation library. 
//
// This sample program iteratively tightens a 
// given formulation by adding cuts, then calls 
// branch-and-bound to solve the tightened
// formulation.
//
// usage:
//   cgl1 mpsFileName objectiveSense
// where:
//   mpsFileName: Name of an mps file (without the
//                file extension)
//   objectiveSense: min for minimization, 
//                   max for maximization. 
// example:
//   cgl1 ../../Data/Sample/p0033 min              
//----------------------------------------------------- 
// The knapsack cut generator assumes the primal solution is feasible.
#include <cassert>
#include <iostream>
#include <string>

#include "CoinError.hpp"
#include "OsiCuts.hpp"
#include "OsiClpSolverInterface.hpp"
//#include "OsiOslSolverInterface.hpp"
#include "CoinWarmStartBasis.hpp"
#include <cassert>

#include "CglKnapsackCover.hpp"
#include "CglSimpleRounding.hpp"

using std::cerr;
using std::cout;
using std::endl;
using std::string;

int main(int argc, const char *argv[])
{
  // If no parms specified then use these
  string mpsFileName;
#if defined(SAMPLEDIR)
  mpsFileName = SAMPLEDIR "/p0033.mps";
#else
  if (argc == 1) {
    fprintf(stderr, "Do not know where to find sample MPS files.\n");
    exit(1);
  }
#endif
  string objSense = "min";

  // Make sure a file name and objective sense or nothing
  // were specified
  if ( argc!=1 && argc!=3 ) {
    cerr <<"Incorrect number of command line parameters." <<endl;
    cerr <<"  usage:" <<endl;
    cerr <<"    "<<argv[0] <<" mpsFileName objectiveSense" <<endl;
    cerr <<"  where:" <<endl;
    cerr <<"    mpsFileName: Name of an mps file" <<endl;
    cerr <<"                 without \".mps\" file extension" <<endl;
    cerr <<"    objectiveSense: min for minimization," <<endl; 
    cerr <<"                    max for maximization." <<endl; 
    return 1;
  }  
  
  // Make sure valid objective sense was specified
  if (argc==3) {
    mpsFileName = argv[1];
    objSense = argv[2];
    if( objSense!="min" && objSense!="max" ){
      cerr <<"Unrecognized objective sense specifed" <<endl;
      cerr <<"  specified value: \"" <<argv[2] <<"\"" <<endl;

      cerr <<"  valid values: \"min\" for minimization," <<endl; 
      cerr <<"                \"max\" for maximization." <<endl; 
      return 1;
    }  
  }
  
  try {
    // Instantiate a specific solver interface
    OsiClpSolverInterface si;
    //OsiOslSolverInterface si;
    
    // Read file describing problem
    si.readMps(mpsFileName.c_str(),"mps"); 
    
    // Set objective min to max
    // First make sure min or max were specified
    if ( objSense=="min" ) si.setObjSense(1.0);
    else si.setObjSense(-1.0);
    
    // Solve continuous problem
    si.initialSolve();

    // Original number of rows (so we can take off inactive cuts)
    int numberRows = si.getNumRows();
    
    // Save the orig lp relaxation value for 
    // comparisons later
    double origLpObj = si.getObjValue();
    
    // Track the total number of cuts applied
    int totalNumberApplied = 0;
    
    // Instantiate cut generators
    CglKnapsackCover cg1;
    CglSimpleRounding cg2;
    
    //---------------------------------------------------
    // Keep applying cuts until 
    //   1. no more cuts are generated
    // or
    //   2. the objective function value doesn't change
    //---------------------------------------------------
    bool equalObj;
    CoinRelFltEq eq(0.0001);
    OsiSolverInterface::ApplyCutsReturnCode acRc;
    double obj;
    
    do {
      // Get current solution value
      obj = si.getObjValue();
      
      // Generate and apply cuts
      OsiCuts cuts;
      cg1.generateCuts(si,cuts);
      cg2.generateCuts(si,cuts);
      acRc = si.applyCuts(cuts,0.0);
      
      // Print applyCuts return code
      cout <<endl <<endl;
      cout <<cuts.sizeCuts() <<" cuts were generated" <<endl;
      cout <<"  " <<acRc.getNumInconsistent() <<" were inconsistent" <<endl;
      cout <<"  " <<acRc.getNumInconsistentWrtIntegerModel() 
           <<" were inconsistent for this problem" <<endl;
      cout <<"  " <<acRc.getNumInfeasible() <<" were infeasible" <<endl;
      cout <<"  " <<acRc.getNumIneffective() <<" were ineffective" <<endl;
      cout <<"  " <<acRc.getNumApplied() <<" were applied" <<endl;
      cout <<endl <<endl;
      
      // Increment the counter of total cuts applied
      totalNumberApplied += acRc.getNumApplied();
      
      // If no cuts were applied, then done
      if ( acRc.getNumApplied()==0 ) break;
      
      // Resolve
      si.resolve();
      
      cout <<endl;
      cout <<"After applying cuts, objective value changed from "
        <<obj <<" to " <<si.getObjValue() <<endl <<endl;

      // Take off slack cuts
      int numberRowsNow = si.getNumRows();
      int * del = new int [numberRowsNow-numberRows];
      const CoinWarmStartBasis* basis = dynamic_cast<const CoinWarmStartBasis*>(si.getWarmStart()) ;
      assert (basis);
      int nDelete=0;
      for (int i=numberRows;i<numberRowsNow;i++) {
	CoinWarmStartBasis::Status status = basis->getArtifStatus(i);
	if (status == CoinWarmStartBasis::basic)
	  del[nDelete++] = i;
      }
      delete basis;
      if (nDelete) {
	si.deleteRows(nDelete,del);
	// should take zero iterations
	si.resolve();
	cout << nDelete << " rows deleted as basic - resolve took " 
	     << si.getIterationCount() <<" iterations"
	     <<endl;
      }
      delete [] del;
      
      // -----------------------------------------------
      // Set Boolean flag to true if new objective is 
      // almost equal to prior value.
      //
      // The test is:
      // abs(oldObj-newObj) <= 0.0001*(CoinMax(abs(oldObj),abs(newObj))+1.);
      // see CoinRelFloatEqual.h 
      // -----------------------------------------------
      equalObj = eq( si.getObjValue(), obj );
    } while( !equalObj );
    
    // Print total number of cuts applied, 
    // and total improvement in the lp objective value
    cout <<endl <<endl;
    cout << "----------------------------------------------------------" 
         <<endl;
    cout << "Cut generation phase completed:" <<endl;
    cout << "   " << totalNumberApplied << " cuts were applied in total," 
         <<endl;
    cout << "   changing the lp objective value from " << origLpObj 
         << " to " << si.getObjValue() <<endl;
    cout << "----------------------------------------------------------" 
         <<endl;
    cout <<endl <<endl;
    
    // If you want to solve problem, change "#if 0" to "#if 1"
#if 0
    // Solve MIP Problem
    si.branchAndBound();
    
    // Print the solution
    cout <<"The objective function value: " <<si.getObjValue() <<endl;
    const double * soln = si.getColSolution();
    int i;
    for ( i=0; i<si.getNumCols(); i ++ ) {
      cout <<" x[" <<i <<"] = " <<soln[i] <<endl;
    }
#endif
  }
  catch ( CoinError e ) {
    cout <<e.className() <<"::" <<e.methodName() <<" - " <<e.message() <<endl;
  }
  
  return 0;
}

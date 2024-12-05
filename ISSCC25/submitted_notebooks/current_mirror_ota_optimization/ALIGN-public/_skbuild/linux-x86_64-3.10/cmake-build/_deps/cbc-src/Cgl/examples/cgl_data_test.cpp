// Copyright (C) 2000, International Business Machines
// Corporation and others.  All Rights Reserved.
// This code is licensed under the terms of the Eclipse Public License (EPL).

#include <cstdio>
#include <cstdlib>
#include <cfloat>

#include "OsiSolverInterface.hpp"
#include "OsiSolverParameters.hpp"
#include "OsiClpSolverInterface.hpp"
#include "CglRedSplit.hpp"
#include "CglRedSplit2.hpp"

int main(int argc, char **argv) 
{
  char *f_name_lp, *last_dot_pos, f_name[256], *f_name_pos;
  int i, ncol;

  if((argc < 2) || (argc > 2)) {
    printf("### ERROR: main(): Usage: One of the following\ncgl_data_test input_file_name.mps\ncgl_data_test input_file_name.lp\n");
    exit(1);
  }

  f_name_lp = strdup(argv[1]);
  f_name_pos = strrchr(f_name_lp, '/');
  if(f_name_pos != NULL) {
    strcpy(f_name, &(f_name_pos[1]));
  }
  else {
    strcpy(f_name, f_name_lp);
  }
  last_dot_pos = strrchr(f_name, '.');
  if(last_dot_pos != NULL) {
    last_dot_pos = '\0';
  }

  // Do for both RedSplit and RedSplit2
  {
    OsiClpSolverInterface *clp = new OsiClpSolverInterface;
    clp->messageHandler()->setLogLevel(0);
    if(strcmp(&(f_name_lp[strlen(f_name_lp)-3]), ".lp") == 0) {
      clp->readLp(f_name_lp);    
    }
    else {
      if(strcmp(&(f_name_lp[strlen(f_name_lp)-4]), ".mps") == 0) {
	clp->readMps(f_name_lp);    
      }
      else {
	printf("### ERROR: unrecognized file type\n");
	exit(1);
      }
    }
    ncol = clp->getNumCols();
    clp->initialSolve();
    
    printf("LP value: %12.2f\n", clp->getObjValue());
    
    OsiCuts cuts;
    
    // Define parameters for CglRedSplit generator
    CglParam cpar;
    cpar.setMAX_SUPPORT(ncol+1);
    CglRedSplitParam rspar(cpar);
    
    // Create a cut generator with the given parameters
    CglRedSplit cutGen(rspar);
    
    char *colType = new char[ncol];
    for(i=0; i<ncol; i++) {
      if(clp->isContinuous(i)) {
	colType[i] = 'C';
      }
      else {
	colType[i] = 'I';
      }
    }
    
    int round, max_rounds = 10;
    for(round=0; round<max_rounds; round++) {
      cutGen.generateCuts(*clp, cuts);
      
      int ncuts = cuts.sizeRowCuts();
      
      const OsiRowCut **newRowCuts = new const OsiRowCut * [ncuts];
      for(i=0; i<ncuts; i++) {
	newRowCuts[i] = &cuts.rowCut(i); 
      }
      clp->applyRowCuts(ncuts, newRowCuts);
      delete[] newRowCuts;
      
      printf("round %4d: %4d generated cuts  new objective value: %12.2f\n", 
	     round, ncuts, clp->getObjValue());
      
      clp->resolve();  
      
      if(clp->isAbandoned()) {
	printf("###ERROR: Numerical difficulties in Solver\n");
	exit(1);
      }
      
      if(clp->isProvenPrimalInfeasible()) {
	printf("### WARNING: Problem is infeasible\n");
	exit(1);
      }
    }
    
    delete clp;
    delete[] colType;
  }
  {
    OsiClpSolverInterface *clp = new OsiClpSolverInterface;
    clp->messageHandler()->setLogLevel(0);
    if(strcmp(&(f_name_lp[strlen(f_name_lp)-3]), ".lp") == 0) {
      clp->readLp(f_name_lp);    
    }
    else {
      if(strcmp(&(f_name_lp[strlen(f_name_lp)-4]), ".mps") == 0) {
	clp->readMps(f_name_lp);    
      }
      else {
	printf("### ERROR: unrecognized file type\n");
	exit(1);
      }
    }
    ncol = clp->getNumCols();
    clp->initialSolve();
    
    printf("LP value: %12.2f\n", clp->getObjValue());
    
    OsiCuts cuts;
    
    // Define parameters for CglRedSplit2 generator
    CglParam cpar;
    cpar.setMAX_SUPPORT(ncol+1);
    CglRedSplit2Param rspar(cpar);
    
    // Create a cut generator with the given parameters
    CglRedSplit2 cutGen(rspar);
    
    char *colType = new char[ncol];
    for(i=0; i<ncol; i++) {
      if(clp->isContinuous(i)) {
	colType[i] = 'C';
      }
      else {
	colType[i] = 'I';
      }
    }
    
    int round, max_rounds = 10;
    for(round=0; round<max_rounds; round++) {
      cutGen.generateCuts(*clp, cuts);
      
      int ncuts = cuts.sizeRowCuts();
      
      const OsiRowCut **newRowCuts = new const OsiRowCut * [ncuts];
      for(i=0; i<ncuts; i++) {
	newRowCuts[i] = &cuts.rowCut(i); 
      }
      clp->applyRowCuts(ncuts, newRowCuts);
      delete[] newRowCuts;
      
      printf("round %4d: %4d generated cuts  new objective value: %12.2f\n", 
	     round, ncuts, clp->getObjValue());
      
      clp->resolve();  
      
      if(clp->isAbandoned()) {
	printf("###ERROR: Numerical difficulties in Solver\n");
	exit(1);
      }
      
      if(clp->isProvenPrimalInfeasible()) {
	printf("### WARNING: Problem is infeasible\n");
	exit(1);
      }
    }
    
    delete clp;
    delete[] colType;
  }
  free(f_name_lp);

  return(0);
}

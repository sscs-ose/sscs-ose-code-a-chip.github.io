/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* The author of this file is Menal Guzelsoy                                 */
/*                                                                           */
/* (c) Copyright 2005-2019 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include "OsiSymSolverInterface.hpp"
#include <iostream>

int main(int argc, char **argv)
{

   /* This example shows how to do some simple stuff with the Osi interface */
   
   /* Create an OsiSym object */
   OsiSymSolverInterface si;

   /* Parse the command line */
   si.parseCommandLine(argc, argv);
   
   /* Read in the problem */
   si.loadProblem();

   int numberofrowstodrop(0);
   int numberofcolstodrop(0);
   int *rowsToDrop(new int[1000]);
   int *colsToDrop(new int[1000]);
   double eps = .0000001;
   int i, j;
   
   /* Find empty rows */

   const double *rhs(si.getRightHandSide());
   const double *obj(si.getObjCoefficients());
   const CoinPackedMatrix *mat(si.getMatrixByCol());
   int numrows = si.getNumRows();
   int numcols = si.getNumCols();
   for (i = 0; i <  numrows; i++) {
      if (fabs(rhs[i]) > eps)
	 continue;
      for (j = 0; j < numcols; j++)
	 if (fabs(mat->getCoefficient(i,j)) > eps ){
	    break;
	 }
      if (j == numcols){
	 cout << "Dropping row " << i << endl;
	 rowsToDrop[numberofrowstodrop++] = i;
      }
   }
   
   /* Find empty columns */

   for (i = 0; i <  numcols; i++) {
      if (fabs(obj[i]) > eps)
	 continue;
      for (j = 0; j < numrows; j++)
	 if (fabs(mat->getCoefficient(j,i)) > eps ){
	    break;
	 }
      if (j == numcols){
	 cout << "Dropping column " << i << endl;
	 rowsToDrop[numberofrowstodrop++] = i;
      }
   }
   
   si.deleteRows(numberofrowstodrop, rowsToDrop);
   si.deleteCols(numberofcolstodrop, colsToDrop);
   
   /* Solve the problem */
   si.branchAndBound();

   return(0);
}


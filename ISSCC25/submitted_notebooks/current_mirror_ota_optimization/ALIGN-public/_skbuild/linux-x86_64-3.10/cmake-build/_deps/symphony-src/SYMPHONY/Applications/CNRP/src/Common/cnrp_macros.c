/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* Capacitated Network Routing Problems.                                     */
/*                                                                           */
/* (c) Copyright 2000-2007 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <math.h>

/* CNRP include files */
#include "cnrp_macros.h"

/*===========================================================================*/

void BOTH_ENDS(int index, int *v0, int *v1)
{
   *v0 = (int)(floor(sqrt(1+8.0*index)/2+.500000001));
   *v1 = index - (*v0 * (*v0-1)/2);
}

/*===========================================================================*/

int NEAREST_INT(double num)
{
   return((num - ((int)num) > ((int)num) + 1 - num) ?
	  (int)ceil(num) : (int)floor(num));
}

/*===========================================================================*/

int INDEX(int v0, int v1)
{
   return( (v1) > (v0) ? ((int)(v1))*((v1)-1)/2+(v0) :
                                      ((int)(v0))*((v0)-1)/2+(v1));
}

/*===========================================================================*/

/*approximates the number of trucks necessary to service a set of customers*/
int BINS(double weight, double capacity)
{
   return((int) ceil(weight/capacity));
}

/*===========================================================================*/

/*calculates the right hand side of a subtour elimination constraint*/
int RHS(int cust_num, double weight, double capacity)
{
   return(cust_num-BINS(weight, capacity));
}

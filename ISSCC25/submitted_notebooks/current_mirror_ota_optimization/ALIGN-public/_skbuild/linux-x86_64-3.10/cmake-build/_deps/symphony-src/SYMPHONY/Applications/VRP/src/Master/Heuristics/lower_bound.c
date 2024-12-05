/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/* This file was modified by Ali Pilatin January, 2005 (alp8@lehigh.edu)     */
/*                                                                           */
/* (c) Copyright 2000-2005 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Common Public License. Please see     */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include <memory.h>
#include <stdio.h>
#include <stdlib.h>

#include "BB_macros.h"
#include "lower_bound.h"
#include "vrp_master_functions.h"
#include "vrp_const.h"
#include "sym_proccomm.h"

/*===========================================================================*/

static int intcompar(const void *int1, const void *int2)
{
   return(*((int *)int2) - *((int *)int1));
}

/*===========================================================================*/

static int sum(int *array, int lower_lim, int upper_lim)
{
   int i, sum;
   
   for (sum = 0, i=lower_lim; i<= upper_lim; i++)
      sum += array[i];
   
   return(sum);
}

/*===========================================================================*/

void lower_bound(vrp_problem *vrp, lb_params *lb_par, heurs *lh, 
		 int ub, int jobs, int *tids, int *sent)
{
   int s_bufid, dummy;
   int y, i, alpha, interval;
   int *sorted_demand, trials;
   int m1, numroutes = vrp->numroutes, capacity = vrp->capacity;
   
   if (!lb_par->lower_bound)
      return;
   
   if (vrp->par.verbosity > 1)
      printf("\nNow beginning lower bounding ....\n\n");
   
   /*Calculate m1 = maximum # of single vehicle routes*/
   
   sorted_demand  = (int *) calloc (vrp->vertnum, sizeof(int));
   
   memcpy (sorted_demand, vrp->demand, vrp->vertnum*sizeof(int));
   qsort (sorted_demand+1, vrp->vertnum-1, sizeof(int), intcompar);
   
   for (m1 = 0;; m1++)
      if (!(capacity*(numroutes-m1-1) >=
	    sum(sorted_demand, m1+2, vrp->vertnum-1)))
	 break;
   
   trials = (lb_par->lower_bound)*(numroutes-m1);
   
   lh->tids = tids;
   
   lh->jobs = jobs;
   
   if (!jobs){
      fprintf(stderr, "\nNo jobs started .... \n\n");
      return;
   }
   
   else if (vrp->par.verbosity >2)
      printf("\n%i jobs started ...\n\n", jobs);
   
   /*-----------------------------------------------------------------------*\
   |                  Broadcast data to the lower bounding procedure         |
   \*-----------------------------------------------------------------------*/
   for(i=0; i<trials; i++){
     s_bufid = init_send(DataInPlace);
     send_int_array(&dummy, 1);
     send_msg(tids[i%jobs], MST);   
     sent[i%jobs]++;
     broadcast(vrp, tids+(i%jobs), 1);
   
     s_bufid = init_send(DataInPlace);
     send_int_array(&numroutes, 1);
     send_int_array(&ub, 1);
     send_int_array(&lb_par->lb_max_iter, 1);
     send_int_array(&m1, 1);
     send_msg(tids[i%jobs],  VRP_LB_DATA);
   }
   interval = lb_par->lb_penalty_mult/lb_par->lower_bound;
   
   for (i=trials-1, y = m1, alpha = lb_par->lb_penalty_mult; i>=0; i--, y++){
      s_bufid = init_send(DataInPlace);
      send_int_array(&y, 1);
      send_int_array(&alpha, 1);
      send_msg(tids[i%jobs], VRP_LB_DATA2);
      if (y == numroutes){
	 y = m1-1;
	 alpha -= interval;
      }
   }
   
   freebuf(s_bufid);
   FREE(sorted_demand);
}

  
  

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
#include <unistd.h>
#include "BB_constants.h"
#include "sym_messages.h"
#include "collect_solutions.h"
#include "compute_cost.h"
#include "vrp_master_functions.h"
#include "network.h"
#include "vrp_const.h"
#include "vrp_macros.h"

/*--------------------------------------------------------------------*\
| The receive_tours function is used to receive the tours              |
| output by various heuristic processes running in parallel and keep   |
| an ordered list of them in a binary tree. It checks about once every |
| second to see if any tours have come into the recieve buffer and if  |
| so, it updates the binary tree and stores the tour if it is one of   |
| the lowest (vrp->par.tours_to_keep) cost tours                       |
\*--------------------------------------------------------------------*/

double collect_solutions(vrp_problem *vrp, int trials, int *last,
			 char add_edges, best_tours *solutions)
{
  printf("in get_rh_solutions... \n");
   int pos;
   int i, round;
   int *tourorder = vrp->tourorder, tournum = -1;
   best_tours *tours = vrp->tours;/*-------------------------------------*\
				  | new best tours are put in this tours* |
				  \*-------------------------------------*/
   int v0, v1, vertnum = vrp->vertnum;
   double total_solve_time = 0;
   edge_data *next_edge = NULL;
   small_graph *g = NULL;
   int newedgenum=0;

   if (add_edges){
      g = vrp->g;
      next_edge = g->edges+g->edgenum;
   }
  

   
   for (round=0; round<trials; round++){

       if (tournum + 1 < vrp->par.tours_to_keep){
	 *last = ++tournum;
	 tours[*last].cost = MAXINT;
       }
       else{
	 *last = tourorder[tournum];
       }
       
       if (tours[*last].cost >solutions[round].cost){ /*check to see if tour is one of *\
						      |the (vrp->par.tours_to_keep)     |
						      |cheapest and if so, update       |
						      \*binary tree                    */
	 tours[*last].cost = solutions[round].cost;
	 tours[*last].numroutes = solutions[round].numroutes;
	 tours[*last].algorithm = solutions[round].algorithm;
	 tours[*last].solve_time += solutions[round].solve_time;
	 total_solve_time += solutions[round].solve_time;//solution time of one batch

	 memcpy((char *)tours[*last].tour, (char *)solutions[round].tour,
		(vertnum) * sizeof(_node));
	 for (pos = tournum -1;
	      pos >=0 &&tours[tourorder[pos]].cost >solutions[round].cost; pos--){
	   tourorder[pos+1]=tourorder[pos];
	 }
	 tourorder[pos+1]=*last;
       }
       
       if (add_edges){
	 v0 = 0;
	 v1 = solutions[round].tour[0].next;
	 for (pos = 0; pos<vertnum; pos++){
	   v1 = solutions[round].tour[v0=v1].next;
	   if(solutions[round].tour[v0].route == solutions[round].tour[v1].route){
	     if (v0 < v1){
	       next_edge->v0 = v0;
	       next_edge->v1 = v1;
	     }
	     else{
	       next_edge->v0 = v1;
	       next_edge->v1 = v0;
	     }
	     if (!bsearch((char *)next_edge, (char *)g->edges,
			  g->edgenum, sizeof(edge_data), is_same_edge)){
	       (next_edge++)->cost = ICOST(&vrp->dist, v0, v1);
	       newedgenum++;
	     }
	   }
	 }//for
       }//if
     
   }//for
     
   if (add_edges && newedgenum){
      g->edgenum += newedgenum;
      delete_dup_edges(g);
   }
   vrp->tournum = tournum;
   for (i=0; i<trials; i++)
     free ((char *)solutions[i].tour);
   free((char *)solutions);
   return(total_solve_time);
}

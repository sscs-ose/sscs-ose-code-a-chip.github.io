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
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include <string.h>
#include <stdio.h>
#include "tsp_ni.h"
#include "sym_constants.h"
#include "tsp_ins_rout.h"
#include "heur_routines.h"
#include "s_path.h"

void tsp_ni(int parent, heur_prob *p)
{
  printf("\nIn tsp_ni....\n\n");
  int mytid, info, r_bufid;
  int starter, nearnode, v0, v1, cur_start;
  _node *tsp_tour, *tour, *opt_tour;
  int mindist;
  int *intour;
  int last, cost;
  int i, j, vertnum;
  neighbor *nbtree;
  int trials, interval;
  best_tours *opt_tours, *tours;
  double t=0;

  mytid = pvm_mytid();

  (void) used_time(&t);

  
  /*------------------------------------------------------------------------*\
  |                     Receive the VRP data                                 |
  \*------------------------------------------------------------------------*/


  PVM_FUNC(r_bufid, pvm_recv(-1, TSP_NI_TRIALS));
  PVM_FUNC(info, pvm_upkint(&trials, 1, 1));
  printf("\nreceived tsp_ni_trials.\n\n");   
  /*------------------------------------------------------------------------*\
  |                     Receive the starting point                           |
  \*------------------------------------------------------------------------*/
  PVM_FUNC(r_bufid, pvm_recv(-1, TSP_START_POINT));
  PVM_FUNC(info, pvm_upkint(&starter, 1, 1));
  vertnum = p->vertnum;
  printf("\nreceived tsp_start_point.\n\n"); 
  if (starter == vertnum)
    for (starter=v0=1, mindist=ICOST(&p->dist, 1,2); v0<vertnum-1; v0++)
      for (v1=v0+1; v1<vertnum; v1++)
	if (mindist > ICOST(&p->dist, v0, v1)){
	  mindist = ICOST(&p->dist, v0, v1);
	  starter = v0;
	}
    printf("\nICOST returned.\n\n"); 
  /*------------------------------------------------------------------------*\
  |                     Allocate arrays                                      |
  \*------------------------------------------------------------------------*/
   tsp_tour   = (_node *)  malloc (vertnum * sizeof(_node));
   nbtree     = (neighbor *) malloc (vertnum * sizeof(neighbor));
   intour     = (int *)      calloc (vertnum, sizeof(int));
   tours      = p->cur_tour = (best_tours *) calloc (1, sizeof(best_tours));
   tour       = p->cur_tour->tour = (_node *) calloc (vertnum, sizeof(_node));
   opt_tours = (best_tours *) malloc (sizeof(best_tours));
   opt_tour  = (_node *) malloc (vertnum*sizeof(_node));
   printf("\nallocated arrays.\n\n"); 
  /*------------------------------------------------------------------------*\
  | This heuristic is a so-called route-first, cluster-second heuristic.     |
  | We first construct a TSP route by nearest insert and then partition it   |
  | into feasible routes by finding a shortest cycle of a graph with edge    |
  | costs bewtween nodes being defined to be the cost of a route from one    |
  | endpoint of the edge to the other.                                       |
  \*------------------------------------------------------------------------*/
   
  /*------------------------------------------------------------------------*\
  |                 Find the nearest insertion tour from 'starter'           |
  \*------------------------------------------------------------------------*/
  last = 0;
  intour[0] = IN_TOUR;
  intour[starter] = IN_TOUR;
  tsp_ni_insert_edges(p, starter, nbtree, intour, &last);
  nearnode = tsp_closest(nbtree, intour, &last);
  intour[nearnode] = IN_TOUR;
  tsp_ni_insert_edges(p, nearnode, nbtree, intour, &last);
  tsp_tour[starter].next = nearnode;
  tsp_tour[nearnode].next = starter;

  cost = 2 * ICOST(&p->dist, starter, nearnode);
  cost = tsp_nearest_ins_from_to(p, tsp_tour, cost, 
			      2, vertnum-1, starter, nbtree, intour, &last);
  printf("\nfound nearest inser from starter.\n\n"); 
  /*------------------------------------------------------------------------*\
  | We must arbitrarily choose a node to be the first node on the first      |
  | route in order to start the partitioning algorithm. The trials variable  |
  | tells us how many starting points to try. Its value is contained in      |
  | p->par.tsp.numstarts.                                                    |
  \*------------------------------------------------------------------------*/

  if (trials > vertnum-1 ) trials = vertnum-1;
  interval = (vertnum-1)/trials;
  opt_tours->cost = MAXINT;

  /*------------------------------------------------------------------------*\
  | Try various partitionings and take the solution that has the least cost  |
  \*------------------------------------------------------------------------*/

   for (i=0, cur_start = starter; i<trials; i++){
     make_routes(p, tsp_tour, cur_start, tours);
     if (tours->cost < opt_tours->cost){
       (void) memcpy ((char *)opt_tours, (char *)tours, sizeof(best_tours));
       (void) memcpy ((char *)opt_tour, (char *)tour, vertnum*sizeof(_node));
     }
     for (j=0; j<interval; j++)
       cur_start = tsp_tour[cur_start].next;
   }
     
  printf("\nfound a solution.\n\n"); 	
   /*-----------------------------------------------------------------------*\
   |              Transmit the tour back to the parent                       |
   \*-----------------------------------------------------------------------*/

  send_tour(opt_tour, opt_tours->cost, opt_tours->numroutes, TSP_NI,
	    used_time(&t), parent, vertnum, 0, NULL);
    printf("\nsent the solution.\n\n"); 
  if ( nbtree ) free ((char *) nbtree);
  if ( intour ) free ((char *) intour);
  if ( opt_tours ) free ((char *) opt_tours);
  if ( opt_tour ) free ((char *) opt_tour);
  if ( tsp_tour ) free ((char *) tsp_tour);
  
  free_heur_prob(p);
  
}

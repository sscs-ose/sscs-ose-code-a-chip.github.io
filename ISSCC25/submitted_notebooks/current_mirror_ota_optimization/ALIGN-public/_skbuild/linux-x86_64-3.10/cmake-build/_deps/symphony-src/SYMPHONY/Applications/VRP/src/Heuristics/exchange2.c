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

#include "exchange2.h"
#include <stdio.h>
void exchange2(int parent, heur_prob *p)
{
  printf("\nIn exchange2....\n\n");
   _node *tour;
  int numroutes;
  int mytid, info, r_bufid;
  int prev_node1, cur_node1, next_node1;
  int prev_node2, cur_node2, next_node2;
  int max_prev1 = 0, max_prev2 = 0, max_next1 = 0, max_next2 = 0;
  int max_node1 = 0, max_node2 = 0;
  best_tours *tours;
  int max_savings = 0, savings;
  int max_route1 = 0, max_route2 = 0, cur_route1, cur_route2;
  route_data *route_info;
  int cont = 1, capacity;
  int *demand;
  double t=0;

  (void) used_time(&t);

  mytid = pvm_mytid();
  
  tours = p->cur_tour = (best_tours *) calloc (1, sizeof(best_tours));
  
  /*-----------------------------------------------------------------------*\
  |                     Receive the starting tour                           |
  \*-----------------------------------------------------------------------*/

  PVM_FUNC(r_bufid, pvm_recv(-1, EXCHANGE_HEUR_TOUR));
  PVM_FUNC(info, pvm_upkbyte((char *)tours, sizeof(best_tours), 1));
  tour = p->cur_tour->tour = (_node *) calloc (p->vertnum, sizeof(_node));
  PVM_FUNC(info, pvm_upkbyte((char *)tour, (p->vertnum)*sizeof(_node), 1));
  numroutes = tours->numroutes;
  route_info = tours->route_info 
             = (route_data *) calloc (numroutes+1, sizeof(route_data));
  route_calc(&p->dist, tour, numroutes, tours->route_info, p->demand);
  capacity = p->capacity;
  demand = p->demand;

  /*------------------------------------------------------------------------*\
  | This loop takes every pair of customers that are on different routes and |
  | considers the savings obtained by switching their positions. After       |
  | considering all possible switches, the switch that is feasible and       |
  | produces the greatest savings is made. This is iterated until no more    |
  | savings can be obtained.                                                 |
  \*------------------------------------------------------------------------*/

  while (cont){
    max_savings = 0;

    /*----------------------------------------------------------------------*\
    | In these nested loops, cur_node1 and cur_node2 are the nodes being     |
    | considered for switching. prev_node1, prev_node2, next_node1, and      |
    | next_node2 are the neighbors of these nodes on their current routes,   |
    | which are denoted by cur_route1 and cur_route2. The current best nodes |
    | to switch are held in max_node1 and max_node2. Their neighbors are     |
    | denoted max_prev1, max_next, max_prev2, and max_next2 respectively     |
    | Since the depot is not included in the node list for the routes, we    |
    | must always be sure to include node zero as a neighbor at the beginning|
    | and end of the routes (see comments below)                             |
    \*----------------------------------------------------------------------*/

    for (cur_route1 = 1; cur_route1 <= numroutes; cur_route1++){
      for (cur_node1 = route_info[cur_route1].first, prev_node1 = 0,
	   next_node1 = tour[cur_node1].next;
	   cur_node1 != route_info[cur_route1].last;
	   prev_node1 = cur_node1, cur_node1 = tour[cur_node1].next,
	   next_node1 = tour[cur_node1].next){
	for (cur_route2 = cur_route1+1; cur_route2 <= numroutes; cur_route2++){
	  for (cur_node2 = route_info[cur_route2].first, prev_node2 = 0,
	       next_node2 = tour[cur_node2].next;
	       cur_node2 != route_info[cur_route2].last;
	       prev_node2 = cur_node2, cur_node2 = tour[cur_node2].next,
	       next_node2 = tour[cur_node2].next){
	    if ((savings = - (ICOST(&p->dist, prev_node1, cur_node2) +
			      ICOST(&p->dist, cur_node2, next_node1) +
			      ICOST(&p->dist, prev_node2, cur_node1) +
			      ICOST(&p->dist, cur_node1, next_node2) -
			      ICOST(&p->dist, prev_node1, cur_node1) -
			      ICOST(&p->dist, cur_node1, next_node1) -
			      ICOST(&p->dist, prev_node2, cur_node2) -
			      ICOST(&p->dist, cur_node2, next_node2))) >
		max_savings){
	      if ((route_info[cur_route1].weight - demand[cur_node1]
		   +demand[cur_node2] <= capacity) && 
		  (route_info[cur_route2].weight - demand[cur_node2]
		   +demand[cur_node1] <= capacity)){
		max_savings = savings;
		max_node1 = cur_node1;
		max_node2 = cur_node2;
		max_prev1 = prev_node1;
		max_prev2 = prev_node2;
		max_next1 = next_node1;
		max_next2 = next_node2;
		max_route1 = cur_route1;
		max_route2 = cur_route2;
	      }
	    }
	  }

	  /*-----------------------------------------------------------------*\
	  | We have now reached the end of cur_route2 and must set next_node2 |
	  | to be zero and repeat the inner loop                              |
	  \*-----------------------------------------------------------------*/

	  next_node2 = 0;
	  if ((savings = - (ICOST(&p->dist, prev_node1, cur_node2) +
			    ICOST(&p->dist, cur_node2, next_node1) +
			    ICOST(&p->dist, prev_node2, cur_node1) +
			    ICOST(&p->dist, cur_node1, next_node2) -
			    ICOST(&p->dist, prev_node1, cur_node1) -
			    ICOST(&p->dist, cur_node1, next_node1) -
			    ICOST(&p->dist, prev_node2, cur_node2) -
			    ICOST(&p->dist, cur_node2, next_node2))) >
	      max_savings){
	    if ((route_info[cur_route1].weight - demand[cur_node1]
		 +demand[cur_node2] <= capacity) && 
		(route_info[cur_route2].weight - demand[cur_node2]
		 +demand[cur_node1] <= capacity)){
	      max_savings = savings;
	      max_node1 = cur_node1;
	      max_node2 = cur_node2;
	      max_prev1 = prev_node1;
	      max_prev2 = prev_node2;
	      max_next1 = next_node1;
	      max_next2 = next_node2;
	      max_route1 = cur_route1;
	      max_route2 = cur_route2;
	    }
	  }
	}
      }
      
      /*---------------------------------------------------------------------*\
      | We have now reached the end of cur_route1 and must set next_node1     |
      | to be 0 and repeat the outer loop                                     |
      \*---------------------------------------------------------------------*/
      
      next_node1 = 0;
      for (cur_route2 = cur_route1+1; cur_route2 <= numroutes; cur_route2++){
	for (cur_node2 = route_info[cur_route2].first, prev_node2 = 0,
	     next_node2 = tour[cur_node2].next;
	     cur_node2 != route_info[cur_route2].last;
	     prev_node2 = cur_node2, cur_node2 = tour[cur_node2].next,
	     next_node2 = tour[cur_node2].next){
	  if ((savings = - (ICOST(&p->dist, prev_node1, cur_node2) +
			    ICOST(&p->dist, cur_node2, next_node1) +
			    ICOST(&p->dist, prev_node2, cur_node1) +
			    ICOST(&p->dist, cur_node1, next_node2) -
			    ICOST(&p->dist, prev_node1, cur_node1) -
			    ICOST(&p->dist, cur_node1, next_node1) -
			    ICOST(&p->dist, prev_node2, cur_node2) -
			    ICOST(&p->dist, cur_node2, next_node2))) >
	      max_savings){
	    if ((route_info[cur_route1].weight - demand[cur_node1]
		 +demand[cur_node2] <= capacity) && 
		(route_info[cur_route2].weight - demand[cur_node2]
		 +demand[cur_node1] <= capacity)){
	      max_savings = savings;
	      max_node1 = cur_node1;
	      max_node2 = cur_node2;
	      max_prev1 = prev_node1;
	      max_prev2 = prev_node2;
	      max_next1 = next_node1;
	      max_next2 = next_node2;
	      max_route1 = cur_route1;
	      max_route2 = cur_route2;
	    }
	  }
	}
	next_node2 = 0;
	if ((savings = - (ICOST(&p->dist, prev_node1, cur_node2) +
			  ICOST(&p->dist, cur_node2, next_node1) +
			  ICOST(&p->dist, prev_node2, cur_node1) +
			  ICOST(&p->dist, cur_node1, next_node2) -
			  ICOST(&p->dist, prev_node1, cur_node1) -
			  ICOST(&p->dist, cur_node1, next_node1) -
			  ICOST(&p->dist, prev_node2, cur_node2) -
			  ICOST(&p->dist, cur_node2, next_node2))) >
	    max_savings){
	  if ((route_info[cur_route1].weight - demand[cur_node1]
	       +demand[cur_node2] <= capacity) && 
	      (route_info[cur_route2].weight - demand[cur_node2]
	       +demand[cur_node1] <= capacity)){
	    max_savings = savings;
	    max_node1 = cur_node1;
	    max_node2 = cur_node2;
	    max_prev1 = prev_node1;
	    max_prev2 = prev_node2;
	    max_next1 = next_node1;
	    max_next2 = next_node2;
	    max_route1 = cur_route1;
	    max_route2 = cur_route2;
	  }
	}
      }
    }
    
    if (max_savings){/* If we found any cost saving switches,
			then make the best one */

      /* Update the route costs */

      route_info[max_route1].cost += ICOST(&p->dist, max_prev1, max_node2) +
	                             ICOST(&p->dist, max_node2, max_next1) -
				     ICOST(&p->dist, max_prev1, max_node1) -
				     ICOST(&p->dist, max_node1, max_next1);
      route_info[max_route2].cost += ICOST(&p->dist, max_prev2, max_node1) +
	                             ICOST(&p->dist, max_node1, max_next2) -
				     ICOST(&p->dist, max_prev2, max_node2) -
				     ICOST(&p->dist, max_node2, max_next2);

      /*--------------------------------------------------------------------*\
      | This is a special case where we need to do the switching a little    |
      | differently because the nodes are adjacent in the route lists, even  |
      | though they are on different routes.                                 |
      \*--------------------------------------------------------------------*/

      if ((!max_next1) && (!max_prev2) && (max_route2 == max_route1+1)){
	route_info[max_route1].last = max_node2;
	route_info[max_route2].first = max_node1;

	/*-------------------------------------------------------------------*\
	| If max_next2 or max_prev1 are 0, we must correct their values so    |
	| that the correct updates in the data structures are made            |
        \*-------------------------------------------------------------------*/

	if (!max_prev1){
	  max_prev1 = route_info[max_route1-1].last;
	  route_info[max_route1].first = max_node2;
	}
	if (!max_next2)
	  route_info[max_route2].last = max_node1;
	if ((!max_next2) && (max_route2 != numroutes))
	  max_next2 = route_info[max_route2+1].first;
	tour[max_prev1].next = max_node2;
	tour[max_node2].next = max_node1;
	tour[max_node1].next = max_next2;
      }
      else{

	/*-------------------------------------------------------------------*\
        | Again as above, if any of max_prev1, max_prev2, max_next1, or       |
	| max_next2 are zero, these values must be corrected so that the data |
	| structure is updated correctly                                      |
        \*-------------------------------------------------------------------*/

	if (!max_prev1){
	  max_prev1 = route_info[max_route1-1].last;
	  route_info[max_route1].first = max_node2;
	}
	if (!max_next1)
	  route_info[max_route1].last = max_node2;
	if ((!max_next1) && (max_route1 != numroutes))
	  max_next1 = route_info[max_route1+1].first;
	if (!max_prev2){
	  max_prev2 = route_info[max_route2-1].last;
	  route_info[max_route2].first = max_node1;
	}
	if (!max_next2)
	  route_info[max_route2].last = max_node1;
	if ((!max_next2) && (max_route2 != numroutes))
	  max_next2 = route_info[max_route2+1].first;
	
	/* Update the tour data structure*/
      
	tour[max_prev1].next = max_node2;
	tour[max_node2].next = max_next1;
	tour[max_prev2].next = max_node1;
	tour[max_node1].next = max_next2;
      }

      /* Update the route_info data structure*/

      route_info[max_route1].weight += demand[max_node2] - demand[max_node1];
      route_info[max_route2].weight += demand[max_node1] - demand[max_node2];
      tour[max_node1].route = max_route2;
      tour[max_node2].route = max_route1;
      tours->cost -= max_savings;
    }
    else cont = 0; /* If no more savings found, then exit */
  }

  /*-----------------------------------------------------------------------*\
  |               Transmit the final tour back to the parent                |
  \*-----------------------------------------------------------------------*/

  send_tour (tour, tours->cost, numroutes, tours->algorithm, used_time(&t),
	     parent, p->vertnum, 0, NULL);

  free_heur_prob(p);

}

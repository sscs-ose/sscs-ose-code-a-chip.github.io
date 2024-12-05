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

#include "exchange.h"
#include <stdio.h>

void exchange (int parent, heur_prob *p)
{
  _node *tour;
  int numroutes;
  int mytid, info, r_bufid;
  int prev_node, cur_node, next_node;
  int v0, v1, insert0 = 0, insert1 = 0, delete0 = 0;
  int delete1 = 0, max_node = 0;
  best_tours *tours;
  int max_savings = 0, savings;
  int cur_route1, cur_route2, insert_route = 0, delete_route = 0;
  route_data *route_info;
  int cont = TRUE, capacity;
  int *demand, count = 0;
  double t = 0;

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
  route_calc(&p->dist, tour, numroutes, route_info, p->demand);
  demand = p->demand;
  capacity = p->capacity;

  /*------------------------------------------------------------------------*\
  | This loop takes every customer and considers inserting it between every  |
  | other pair of customers on all other routes. After considering all these |
  | moves, the one that is feasible and results in the greatest cost savings |
  | is made. This is iterated until no more cost saving moves can be found.  |
  \*------------------------------------------------------------------------*/

  while (cont){ /* while the last iteration produced a savings */
    max_savings = 0;

    /*----------------------------------------------------------------------*\
    | In these nested loops, cur_node is the node being considered for       |
    | relocation. cur_route1 is the route on which that node is located.     |
    | prev_node and next_node are the neighbors of that node in the solution |
    | cur_route2 is the route being considered for relocation. v0 and v1 are |
    | the two nodes between which we are considering inserting cur_node.     |
    | max_savings denotes the greatest savings found so far. max_node denotes|
    | the node whose relocation gives that savings. insert0 and insert1      |
    | denote where that node should be inserted in order to achieve that     |
    | savings. delete0 and delete1 denote the neighbors of max_node in its   |
    | original position. Since the depot is not included in the node list for|
    | the routes, we must always make sure to include node zero as a neighbor|
    | at the beginning and end of each route (see comments below)            |
    \*----------------------------------------------------------------------*/

    for (cur_route1 = 1; cur_route1 <= numroutes; cur_route1++){
      for (cur_node = route_info[cur_route1].first, 
	   prev_node = 0, 
	   next_node = tour[cur_node].next; 
	   cur_node != route_info[cur_route1].last; 
	   prev_node = cur_node, cur_node = tour[cur_node].next,
	   next_node = tour[cur_node].next){
	for (cur_route2 = 1; cur_route2 <= numroutes; cur_route2++){
	  for (v0 = 0, v1 = route_info[cur_route2].first; 
	       v0 != route_info[cur_route2].last; v0=v1, v1=tour[v1].next)
	    if (((savings = -((ICOST(&p->dist, v0, cur_node) + ICOST(&p->dist,
			       cur_node, v1) - ICOST(&p->dist, v0, v1))
	        + (ICOST(&p->dist, prev_node, next_node) -
		   (ICOST(&p->dist, prev_node, cur_node) +
	        ICOST(&p->dist, cur_node, next_node))))) > max_savings ) 
                && (v0 != cur_node) && (v1 != cur_node) 
	        && (demand[cur_node] + route_info[cur_route2].weight <=
		   capacity)){
	      max_savings = savings;
	      max_node = cur_node;
	      insert0 = v0;
	      insert1 = v1;
	      delete0 = prev_node;
	      delete1 = next_node;
	      insert_route = cur_route2;
	      delete_route = cur_route1;
	    }

	  /*-----------------------------------------------------------------*\
	  | We have now reached the end of cur_route2 and must set v1 to be   |
	  | zero and repeat the inner loop                                    |
	  \*-----------------------------------------------------------------*/

	  v1 = 0;
	  if (((savings = -((ICOST(&p->dist, v0, cur_node) +
			     ICOST(&p->dist, cur_node, v1) -
			     ICOST(&p->dist, v0, v1))
			    + (ICOST(&p->dist, prev_node, next_node) -
			       (ICOST(&p->dist, prev_node, cur_node) +
				ICOST(&p->dist, cur_node, next_node)))))
	       > max_savings ) 
              && (v0 != cur_node) & (v1 != cur_node) 
	      && (demand[cur_node] + route_info[cur_route2].weight <=
		 capacity)){
	    max_savings = savings;
	    max_node = cur_node;
	    insert0 = v0;
	    insert1 = v1;
	    delete0 = prev_node;
	    delete1 = next_node;
	    insert_route = cur_route2;
	    delete_route = cur_route1;
	  }
	}
      }

      /*---------------------------------------------------------------------*\
      | We have now reached the end of cur_route1 and must set next_node to   |
      | be 0 and repeat the outer loop                                        |
      \*---------------------------------------------------------------------*/

      next_node = 0;
      for (cur_route2 = 1; cur_route2 <= numroutes; cur_route2++){
	for (v0 = 0, v1 = route_info[cur_route2].first; 
	     v0 != route_info[cur_route2].last; v0=v1, v1=tour[v1].next)
	  if (((savings = -((ICOST(&p->dist, v0, cur_node) + ICOST(&p->dist,
	       cur_node, v1) - ICOST(&p->dist, v0, v1))
	      + (ICOST(&p->dist, prev_node, next_node) -
		 (ICOST(&p->dist, prev_node, cur_node) +
	      ICOST(&p->dist, cur_node, next_node))))) > max_savings ) 
              && (v0 != cur_node) & (v1 != cur_node) 
	      && (demand[cur_node] + route_info[cur_route2].weight <=
		 capacity)){
	    max_savings = savings;
	    max_node = cur_node;
	    insert0 = v0;
	    insert1 = v1;
	    delete0 = prev_node;
	    delete1 = next_node;
	    insert_route = cur_route2;
	    delete_route = cur_route1;
	  }
	v1 = 0;
	if (((savings = -((ICOST(&p->dist, v0, cur_node) +
			   ICOST(&p->dist, cur_node, v1) -
			   ICOST(&p->dist, v0, v1))
	      + (ICOST(&p->dist, prev_node, next_node) -
		 (ICOST(&p->dist, prev_node, cur_node) +
	      ICOST(&p->dist, cur_node, next_node))))) > max_savings ) 
              && (v0 != cur_node) & (v1 != cur_node) 
	      && (demand[cur_node] + route_info[cur_route2].weight <=
		 capacity)){
	  max_savings = savings;
	  max_node = cur_node;
	  insert0 = v0;
	  insert1 = v1;
	  delete0 = prev_node;
	  delete1 = next_node;
	  insert_route = cur_route2;
	  delete_route = cur_route1;
	}
      }
    }
  
    if (max_savings){ /* If we found any cost saving moves, then make the
			 best one */

      /* Update the route costs */

      count++;
      route_info[delete_route].cost += (ICOST(&p->dist, delete0, delete1) - 
	                          (ICOST(&p->dist, delete0, max_node) +
				   ICOST(&p->dist, max_node, delete1)));
      route_info[insert_route].cost += (ICOST(&p->dist, insert0, max_node) + 
					ICOST(&p->dist, max_node, insert1) -
					ICOST(&p->dist, insert0, insert1));

      /*---------------------------------------------------------------------*\
      | If max_node is the only customer left on the route, then we must      |
      | delete the route We must also reset delete0 and delete1 so that the   |
      | correct updates are made                                              |
      \*-----------------------------------_---------------------------------*/

      if ((!delete0) && (!delete1)){
	delete0 = route_info[(delete_route)-1].last;
	if (delete_route != numroutes)
	    delete1 = route_info[delete_route+1].first;
	numroutes -= 1;
	for (cur_route1 = delete_route; cur_route1 <= numroutes; cur_route1++){
	  route_info[cur_route1] = route_info[cur_route1+1];
	}
	for (cur_node = route_info[delete_route].first; cur_node !=0;
	     cur_node = tour[cur_node].next)
	  tour[cur_node].route -= 1;
	if (insert_route > tour[max_node].route)
	  insert_route -= 1;
      }
      else{

	/*-------------------------------------------------------------------*\
	| If delete0 or delete1 are 0, we must reset their values so that the |
	| correct updates in the data structure are made. Also, the first or  |
	| last nodes of  the route my have to be updated                      |
	\*-------------------------------------------------------------------*/

	if (!delete0){
	  delete0 = route_info[(delete_route)-1].last;
	  route_info[delete_route].first = delete1;
	}
	if (!delete1)
	  route_info[delete_route].last = delete0;
	if ((!delete1) && (delete_route != numroutes))
	  delete1 = route_info[(delete_route)+1].first;
	route_info[delete_route].numcust -=1;
	route_info[delete_route].weight -= demand[max_node];
      }

      /*---------------------------------------------------------------------*\
      | Here, we might also have to reset insert0 and insert1 and the first   |
      | and last nodes of the route where max_node is to be inserted          |
      \*---------------------------------------------------------------------*/

      if (!insert0){
	insert0 = route_info[insert_route-1].last;
	route_info[insert_route].first = max_node;
      }
      if (!insert1)
	route_info[insert_route].last = max_node;
      if ((!insert1) && (insert_route != numroutes))
	insert1 = route_info[insert_route+1].first;

      /* Update the tour and route_info data structures */

      tour[delete0].next = delete1;
      tour[insert0].next = max_node;
      tour[max_node].next = insert1;
      route_info[insert_route].weight += demand[max_node];
      route_info[insert_route].numcust += 1;
      tour[max_node].route = insert_route;
      tours->cost -= max_savings;
    }
    else cont = FALSE; /* If no savings is found, exit */
  }

  /*-----------------------------------------------------------------------*\
  |              Transmit the final tour back to the parent                 |
  \*-----------------------------------------------------------------------*/

  send_tour (tour, tours->cost, numroutes, tours->algorithm, used_time(&t),
	     parent, p->vertnum, 0, NULL);

  free_heur_prob(p);

}		  
  
	    
	    

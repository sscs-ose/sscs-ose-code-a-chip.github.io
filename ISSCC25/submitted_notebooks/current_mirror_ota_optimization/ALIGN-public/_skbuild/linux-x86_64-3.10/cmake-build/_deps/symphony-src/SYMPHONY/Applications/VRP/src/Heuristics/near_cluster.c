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

#include "near_cluster.h"
#include <stdio.h>
void near_cluster(int parent,  heur_prob *p)
{
  printf("\nIn near_cluster....\n\n");
  int vertnum;
  int mytid, info, r_bufid;
  int cost, zero_cost = 0;
  int *intour, last = 0;
  int numroutes, i;
  neighbor *nbtree;
  _node *tour;
  route_data *route_info;
  int cur_route;
  best_tours *tours;
  double t=0;

  (void) used_time(&t);

  mytid = pvm_mytid();
	
  tours = p->cur_tour = (best_tours *) calloc (1, sizeof(best_tours));
	
  /*-----------------------------------------------------------------------*\
  |                    Receive the VRP data                                 |
  \*-----------------------------------------------------------------------*/

  PVM_FUNC(r_bufid, pvm_recv(-1, NC_NUMROUTES));
  PVM_FUNC(info, pvm_upkint(&p->numroutes, 1, 1));
 
  vertnum = p->vertnum;
  numroutes = p->numroutes;

  /*-----------------------------------------------------------------------*\
  |                    Allocate arrays                                      |
  \*-----------------------------------------------------------------------*/

  nbtree   = (neighbor *) malloc (vertnum * sizeof(neighbor));
  intour   = (int *)      calloc (vertnum, sizeof(int));
  tour = p->cur_tour->tour
       = (_node *) calloc (vertnum, sizeof(_node));

  /*-----------------------------------------------------------------------*\
  | First we generate seed customers for all the routes                     |
  \*-----------------------------------------------------------------------*/

  seeds2(p, &numroutes, intour, nbtree);

  route_info = p->cur_tour->route_info;

  p->cur_tour->numroutes = numroutes;

  /*-----------------------------------------------------------------------*\
  | This algorithm builds all routes simultaneously. For each customer not  |
  | already in the solution, it keeps track of the route that it is closest |
  | to (i.e. the route # of the customer already in the solution that it is |
  | closest to). At each step, the customer in closest proximity to its host|
  | route is added to that route and all distances are updated. If it is    |
  | found to be infeasible to add the customer to the route, then a new host|
  | is found and we start the process again. Note that as we go through the |
  | algorithm, the last node of each route always points towards the depot  |
  \*-----------------------------------------------------------------------*/

  if (nbtree) free ((char *) nbtree);

  nbtree = (neighbor *) calloc (vertnum, sizeof(neighbor));

  for( i = 0; i<vertnum; i++){
    if (intour[i] != IN_TOUR)
      intour[i] = 0;
    tour[i].next = 0;
  }
  
  for (cur_route = 1; cur_route<=numroutes; cur_route++)
    ni_insert_edges2(p, route_info[cur_route].first, nbtree, intour, &last,
		    tour, route_info);
  
  /* Form the routes by nearest insertion as described above */
    
  nearest_ins2(p, tour, route_info, numroutes+1, vertnum,
		      nbtree, intour, &last, &zero_cost);
  if(!zero_cost){
  tour[0].next = route_info[1].first;

  
  /*-------------------------------------------------------------------------*\
  | This loop points the last node of each route to the first node of the next|
  | route. At the end of this procedure, the last node of each route is       |
  | pointing at the depot, which is not what we want.                         |
  \*-------------------------------------------------------------------------*/

  for (cur_route = 1; cur_route < numroutes; cur_route++)
    tour[route_info[cur_route].last].next = route_info[cur_route+1].first;

  cost = compute_tour_cost(&p->dist, tour);
	
  /*-----------------------------------------------------------------------*\
  |               Transmit the tour back to the parent                      |
  \*-----------------------------------------------------------------------*/
  
  send_tour(tour, cost, numroutes, NEAR_CLUSTER, used_time(&t), parent,
	    vertnum, 1, route_info);
	
  if ( nbtree ) free ((char *) nbtree);
  if ( intour ) free ((char *) intour);

  free_heur_prob(p);
  }	
}

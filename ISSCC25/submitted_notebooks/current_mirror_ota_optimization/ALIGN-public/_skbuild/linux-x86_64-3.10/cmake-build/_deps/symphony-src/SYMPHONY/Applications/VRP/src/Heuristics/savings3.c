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

#include <stdio.h>

#include "savings3.h"
#include "sym_macros.h"
#include "sym_constants.h"
#include "heur_routines.h"
#include "ins_routines2.h"
#include "binomial.h"
#include "vrp_common_types.h"

#ifndef _SAV
#define _SAV
#define SAV(d, a, b, c) (p->par.savings_par.lamda) * ICOST(d, 0, c) - \
                               (ICOST(d,a,c) + ICOST(d,b,c) -  \
			        (p->par.savings_par.mu) * ICOST(d,a,b))
#endif

void insert_cust3 PROTO((int cust_num, _node *tour, int node1,
			int node2, int cur_route, int *demand,
			route_data *route_info));
tree_node *update_savings3 PROTO((heur_prob *p, tree_node *head,
				 tree_node *max_ptr, _node *tour,
				 route_data *route_info));
int find_new_ins_route3 PROTO((heur_prob *p, int ins_node, _node *tour,
			      int *node1, int *node2,
			      route_data *route_info));

void savings3(int parent, heur_prob *p)
{
  printf("\nIn savings3....\n\n");
   _node *tour;
   int mytid, info, r_bufid;
   int i, capacity;
   int vertnum;
   int cur_route=1;
   int *demand;
   tree_node *head, *max_ptr;
   int savings, *intour, max_savings;
   int numroutes, v0, v1, ins_route, cust_num;
   double t=0;
   neighbor *nbtree;
   route_data *route_info;

   mytid = pvm_mytid();
   (void) used_time(&t);
   
   
   /*-----------------------------------------------------------------------*\
   |                     Receive the parameters                              |
   \*-----------------------------------------------------------------------*/

   PVM_FUNC(r_bufid, pvm_recv(-1, S3_NUMROUTES));
   PVM_FUNC(info, pvm_upkint(&p->numroutes, 1, 1));
   PVM_FUNC(r_bufid, pvm_recv(-1, SAVINGS3_DATA));
   printf("\nCheckpoint 1\n");
   PVM_FUNC(info, pvm_upkfloat(&p->par.savings_par.mu, 1, 1));
   PVM_FUNC(info, pvm_upkfloat(&p->par.savings_par.lamda, 1, 1));
   capacity = p->capacity;
   vertnum = p->vertnum;
   demand = p->demand;
   numroutes = p->numroutes;
   
   p->cur_tour = (best_tours *) calloc (1, sizeof(best_tours));
   tour = p->cur_tour->tour = (_node *) calloc (vertnum, sizeof(_node));
   intour   = (int *)      calloc (vertnum, sizeof(int));
   nbtree   = (neighbor *) malloc (vertnum * sizeof(neighbor));
   
   seeds2(p, &numroutes, intour, nbtree);

   p->numroutes = numroutes;
   
   route_info = p->cur_tour->route_info;
   p->cur_tour->numroutes = numroutes;

   for( i = 0; i<vertnum; i++){
      if (intour[i] != IN_TOUR)
	 intour[i] = 0;
      tour[i].next = 0;
   }
   printf("\nCheckpoint 2\n");   
   for (i = 0; intour[i] == IN_TOUR; i++);
   for (max_savings = MAXINT, cur_route = 1; cur_route <= numroutes;
	cur_route++){
     if ((savings = (int) (SAV(&p->dist, 0, route_info[cur_route].first, i)))
	  < max_savings){
	 max_savings = savings;
	 v1 = route_info[cur_route].first;
      }
   }
   head = make_heap(i, max_savings, 0, v1);
   
   /*----------------------------------------------------------*\
   |          Make the initial heap                             |
   \*----------------------------------------------------------*/
   
   for (i++; i<vertnum; i++){
      if (intour[i] == IN_TOUR)
	 continue;
      for (max_savings = MAXINT, cur_route = 1; cur_route <= numroutes;
	   cur_route++){
	if (((savings = (int) (SAV(&p->dist, 0, route_info[cur_route].first, i)))
	      < max_savings) && (route_info[cur_route].weight +
				 demand[i] <= capacity)){
	    max_savings = savings;
	    v1 = route_info[cur_route].first;
	 }
      }
      head = heap_insert(head, i, max_savings, 0, v1);
   }
   printf("\nCheckpoint 3\n");      
   /*------------------------------------------------------------------*\  
   |  The following loop first finds the customer with the maximum      |
   |  savings among all customers not yet put on routes and returns the |
   |  the position in which to insert the customer in order to achieve  |
   |  that savings. It then checks the feasibility of inserting that    |
   |  that customer on the current route and if it is infeasible, starts|
   |  a new route.                                                      |
   \*------------------------------------------------------------------*/

   cust_num = numroutes+1;
   while (head != NULL){
      max_ptr = find_max(head);
      head = extract_max(head, max_ptr);
      ins_route = max_ptr->node1 ? tour[max_ptr->node1].route :
	 tour[max_ptr->node2].route;
      if (route_info[ins_route].weight+demand[max_ptr->cust_num] <= capacity){
	 insert_cust3(max_ptr->cust_num, tour, max_ptr->node1,
		     max_ptr->node2, ins_route, demand, route_info);
	 head = update_savings3(p, head, max_ptr, tour, route_info);
	 cust_num++;
      }else{
	 savings = find_new_ins_route3(p, max_ptr->cust_num, tour, &v0, &v1,
				      route_info);
	 if (savings == -MAXINT){
	    head = NULL;
	    continue;
	 }
	 head = heap_insert(head, max_ptr->cust_num, savings, v0, v1);
      }
      FREE(max_ptr);
   }
   printf("\nCheckpoint 4\n");
   tour[0].next = route_info[1].first;
   
   /*------------------------------------------------------------------------*\
   | This loop points the last node of each route to the first node of the    |
   | next route. At the end of this procedure, the last node of each route is |
   | pointing at the depot, which is not what we want.                        |
   \*------------------------------------------------------------------------*/

   for (cur_route = 1; cur_route < numroutes; cur_route++)
      tour[route_info[cur_route].last].next = route_info[cur_route+1].first;
      
   if (cust_num != vertnum){
      printf(
       "\n\nError: customer cannot be inserted on any route .... aborting!\n");
      p->cur_tour->cost = 0;
   }else{
      p->cur_tour->cost = compute_tour_cost(&p->dist, tour);
   }
   
   /*-----------------------------------------------------------------------*\
   |               Transmit the tour back to the parent                      |
   \*-----------------------------------------------------------------------*/
   
   send_tour(tour, p->cur_tour->cost, p->cur_tour->numroutes, SAVINGS3,
	     used_time(&t), parent, vertnum, 0, NULL);
   printf("\nCheckpoint 5\n");
   FREE(intour);
   FREE(nbtree);
   
   free_heur_prob(p);
   printf("\nCheckpoint 6\n");   
}
      
      

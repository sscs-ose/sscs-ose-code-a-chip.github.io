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

#include <stddef.h>

#include "sym_constants.h"
#include "binomial.h"
#include "savings3.h"//lazimmi dene
#include "ins_routines2.h"
#include "vrp_const.h"
#include "compute_cost.h"

/*------------------------------------------------------------------*\  
| This function inserts cust_num into the current route between node1|
| and node2.                                                         |
\*------------------------------------------------------------------*/
int find_new_ins_route3(heur_prob *p, int ins_node,
		       _node *tour, int *node1, int *node2,
			route_data *route_info);
#ifndef _SAV
#define _SAV
#define SAV(d, a, b, c) (p->par.savings_par.lamda) * ICOST(d, 0, c) - \
                       (ICOST(d,a,c) + ICOST(d,b,c) -  \
			(p->par.savings_par.mu) * ICOST(d,a,b))
#endif

void insert_cust3(int cust_num, _node *tour, int node1, int node2,
		 int cur_route, int *demand, route_data *route_info)
{
   if (node1 == 0){
      route_info[cur_route].first = cust_num;
      tour[cust_num].next = node2;
   }else if (node2 == 0){
      route_info[cur_route].last = cust_num;
      tour[node1].next = cust_num;
   }else{
      tour[node1].next = cust_num;
      tour[cust_num].next = node2;
   }
   tour[cust_num].route = cur_route;
   route_info[cur_route].weight += demand[cust_num];
   return;
}

/*===========================================================================*/

/*-----------------------------------------------------------------------*\
| This function updates the savings number of a node following the        |
| insertion of a new node onto the current route. If the old insertion    |
| point of the node still exists (i.e. if the new node was not inserted   |
| there, then we need only calculate the savings for the two possible new |
| insertion points created by the addition of the new node to the route.  |
| Otherwise, we need to start from scratch and recalculate the savings for|
|  all possible insertion points.                                         |
\*-----------------------------------------------------------------------*/

int new_savings3(heur_prob *p, tree_node *max_ptr, tree_node *head, _node *tour,
		int *node1, int *node2, route_data *route_info)
{
   int savings, max_savings;
   int ins_route = max_ptr->node1 ? tour[max_ptr->node1].route :
      tour[max_ptr->node2].route;
   
   if (((head->node1 == max_ptr->node1) && (head->node2 == max_ptr->node2)) ||
       (route_info[ins_route].weight + p->demand[max_ptr->cust_num] >=
	p->capacity)){
      max_savings = find_new_ins_route3(p, head->cust_num, tour, node1, node2,
				       route_info);
      return(max_savings);
   }
   
   if ((savings = (int) (SAV(&p->dist, max_ptr->node1, max_ptr->cust_num,
		      head->cust_num))) > head->savings){
      *node1 = max_ptr->node1;
      *node2 = max_ptr->cust_num;
      max_savings = savings;
   }
   else if ((savings = (int) (SAV(&p->dist, max_ptr->cust_num, max_ptr->node2,
			   head->cust_num))) > head->savings){
      *node1 = max_ptr->cust_num;
      *node2 = max_ptr->node2;
      max_savings = savings;
   }
   else{
      *node1 = head->node1;
      *node2 = head->node2;
      max_savings = head->savings;
   }
   return(max_savings);
}

/*===========================================================================*/

/*---------------------------------------------------------------------------*\
| This function updates the heap after a new node has been addded to the      |
| solution. It walks through the current heap, recalculates the savings       |
| numbers and merges each node into a new heap.                               |
\*---------------------------------------------------------------------------*/
  
tree_node *update_savings3(heur_prob *p, tree_node *head, tree_node *max_ptr,
			  _node *tour, route_data *route_info)
{
  tree_node *temp1, *temp2;
  int savings;
  int degree;
  tree_node *new_head;
  int node1, node2;

  if (head == NULL) return(NULL);

  temp1 = head->child;
  temp2 = head->sibling;
  savings = new_savings3(p, max_ptr, head, tour, &node1, &node2, route_info);
  if (savings == -MAXINT)
     return(NULL);
  new_head = make_heap(head->cust_num, savings, node1, node2);
  degree = head->degree;
  free(head);

  if (degree >0){
    temp1 = update_savings3(p, temp1, max_ptr, tour, route_info);
    if (!temp1)
       return(NULL);
    new_head = merge_heaps(temp1, new_head);
  }

  if (temp2!=NULL){
    temp2 = update_savings3(p, temp2, max_ptr, tour, route_info);
    if (!temp2)
       return(NULL);
    new_head = merge_heaps(temp2, new_head);
  }
  if(!degree && !temp2 &&!new_head) return(NULL);
  else return(new_head);
}

/*===========================================================================*/

int find_new_ins_route3(heur_prob *p, int ins_node,
		       _node *tour, int *node1, int *node2,
		       route_data *route_info)
{
   int max_savings, savings;
   int cur_route, cur_node, prev_node;
   int weight = p->demand[ins_node];
   
   for (max_savings = -MAXINT, cur_route = 1; cur_route <= p->numroutes;
	cur_route++){
      if (route_info[cur_route].weight + weight > p->capacity)
	 continue;
      cur_node = route_info[cur_route].first;
      prev_node = 0;
      for (; cur_node; prev_node = cur_node, cur_node = tour[cur_node].next){
	if ((savings = (int) (SAV(&p->dist, prev_node, cur_node, ins_node)))
	     > max_savings){
	    max_savings = savings;
	    *node1 = prev_node;
	    *node2 = cur_node;
	 }
      }
   }

   return(max_savings);
}

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

#include <stdlib.h>
#include <stdio.h>

#include "sym_constants.h"
#include "binomial.h"
#include "savings2.h"//lazimmi dene
#include "vrp_const.h"
#include "compute_cost.h"

#ifndef _SAV
#define _SAV
#define SAV(d, a, b, c) (p->par.savings_par.lamda) * ICOST(d, 0, c) - \
                       (ICOST(d,a,c) + ICOST(d,b,c) -  \
			(p->par.savings_par.mu) * ICOST(d,a,b))
#endif

/*------------------------------------------------------------------*\  
| This function inserts cust_num into the current route between node1|
| and node2.                                                         |
\*------------------------------------------------------------------*/

void insert_cust2(int cust_num, _node *tour, int node1,
		 int node2, int cur_route, int end_of_route)
{
  if (node1 == 0){
    tour[end_of_route].next = cust_num;
    tour[cust_num].route = cur_route;
    tour[cust_num].next = node2;
  }
  else{
    tour[node1].next = cust_num;
    tour[cust_num].next = node2;
    tour[cust_num].route = cur_route;
  }
  return;
}

/*===========================================================================*/

/*-------------------------------------------------------------------*\
| This function starts a new heap for the next route by walking       |
| through the current heap, computing the new savings value for each  |
| customer encountered and inserting that customer in the new heap    |
\*-------------------------------------------------------------------*/

tree_node *start_new_route2(heur_prob *p, tree_node *head, int starter)
{
  tree_node *temp1, *temp2;
  int savings;
  int degree;
  tree_node *new_head = NULL;

  temp1 = head->child;
  temp2 = head->sibling;
  degree = head->degree;

  if (head->cust_num == starter){
    free(head);
    head = NULL;
  }
  else{
    savings = (int) (SAV(&p->dist, 0, starter, head->cust_num));
    new_head = make_heap(head->cust_num, savings, 0, starter);
    degree = head->degree;
    free(head);
  }

  if (degree >0){
    temp1 = start_new_route2 (p, temp1, starter);
    if (!head)
      new_head = temp1;
    else
      new_head = merge_heaps(temp1, new_head);
  }

  if (temp2 != NULL){
    temp2 = start_new_route2 (p, temp2, starter);
    if (!head && !degree)
      new_head = temp2;
    else
      new_head = merge_heaps(temp2, new_head);
  }
  if (!degree && !temp2 && !head) return(NULL);
  else return(new_head);
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

int new_savings2(heur_prob *p, tree_node *max_ptr, tree_node *head, _node *tour,
		int prev_route_end, int *node1, int *node2)
{
  int v0 = 0, v1;
  int savings, temp_savings;

  if ((head->node1 == max_ptr->node1) && (head->node2 == max_ptr->node2)){
    v1 = tour[prev_route_end].next;
    savings = (int) (SAV (&p->dist, 0, v1, head->cust_num));
    *node1 = v0;
    *node2 = v1;

    do{
      v1 = tour[v0=v1].next;
      if (SAV (&p->dist, v1, v0, head->cust_num) > savings){
	savings = (int) (SAV(&p->dist, v0, v1, head->cust_num));
	*node1 = v0;
	*node2 = v1;
      }
    }while (v1 != 0);
  }
  else{
    if ((temp_savings = (int) (SAV(&p->dist, max_ptr->node1,
				   max_ptr->cust_num, head->cust_num)))
	> head->savings){
      *node1 = max_ptr->node1;
      *node2 = max_ptr->cust_num;
      savings = (int) (SAV(&p->dist, max_ptr->node1,
			   max_ptr->cust_num, head->cust_num));
    }
    else if ((temp_savings = (int) (SAV(&p->dist, max_ptr->cust_num,
					max_ptr->node2, head->cust_num)))
	     > head->savings){
      *node1 = max_ptr->cust_num;
      *node2 = max_ptr->node2;
      savings = (int) (SAV(&p->dist, max_ptr->cust_num,
			   max_ptr->node2, head->cust_num));
    }
    else{
      *node1 = head->node1;
      *node2 = head->node2;
      savings = head->savings;
    }
  }
  return(savings);
}

/*===========================================================================*/

/*---------------------------------------------------------------------------*\
| This function updates the heap after a new node has been addded to a route. |
| It walks through the current heap, recalculates the savings numbers and     |
| merges each node into a new heap.                                           |
\*---------------------------------------------------------------------------*/
  
tree_node *update_savings2(heur_prob *p, tree_node *head, tree_node *max_ptr,
			  _node *tour, int prev_route_end)
{
  tree_node *temp1, *temp2;
  int savings;
  int degree;
  tree_node *new_head;
  int node1, node2;

  if (head == NULL) return(NULL);

  temp1 = head->child;
  temp2 = head->sibling;
  savings = new_savings2(p, max_ptr, head, tour, prev_route_end, &node1, &node2);
  new_head = make_heap(head->cust_num, savings, node1, node2);
  degree = head->degree;
  free(head);

  if (degree >0){
    temp1 = update_savings2(p, temp1, max_ptr, tour, prev_route_end);
    new_head = merge_heaps(temp1, new_head);
  }

  if (temp2!=NULL){
    temp2 = update_savings2(p, temp2, max_ptr, tour, prev_route_end);
    new_head = merge_heaps(temp2, new_head);
  }
  if(!degree && !temp2 &&!new_head) return(NULL);
  else return(new_head);
}
  
/*===========================================================================*/

/*---------------------------------------------------------------------*\
| This function prints the current routes to stdout. It is for debugging|
| purposes only.                                                        |
\*---------------------------------------------------------------------*/

void print_routes2(_node *tour)
{
  int prev_node = 0, node = tour[0].next;

  while (node != 0){
    if (tour[prev_node].route != tour[node].route)
      printf("\nRoute #%i: ", tour[node].route);
    printf("%i ", node);
    prev_node = node;
    node = tour[node].next;
  }
  printf("\n\n");
  return;
}

/*===========================================================================*/

/*--------------------------------------------------------------------*\
| This function computes the starter for a new route. It either returns|
| the farthest customer from the depot that is not yet on a route or it|
| returns a random node that is not yet on a route, depending on the   |
| value of the variable start.                                         |
\*--------------------------------------------------------------------*/

int new_start2(int *intour, heur_prob *p, int start,
		  int num_cust)
{
  int starter = 0, start_pos, count=0, i=0;
  int cost = -MAXINT;
  int vertnum = p->vertnum;

  if (start == FAR_INS)
    for (i=1; i<vertnum; i++){
      if ((ICOST(&p->dist, 0, i) > cost) &&
	  (intour[i] != IN_TOUR)){
	starter = i;
	cost = ICOST(&p->dist, 0, i);
      }
    }
  else{
    start_pos = rand()%num_cust+1;
    do{
      i++;
      if (intour[i] != IN_TOUR) count++;
    }while (count < start_pos);
    starter = i;
  }
      
  return(starter);
}


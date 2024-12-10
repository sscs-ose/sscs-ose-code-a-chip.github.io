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
#include <stdlib.h>

#include "sym_constants.h"
#include "savings.h"//lazimmi dene
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
#ifndef _INSERT_CUST
#define _INSERT_CUST
void insert_cust(int cust_num, _node *tour, int node1,
		 int node2, int cur_route,
		 int prev_route_end)
{
  if (node1 == 0){
    tour[prev_route_end].next = cust_num;
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
#endif
/*===========================================================================*/

/*---------------------------------------------------------------------*\
| This function prints the current routes to stdout. It is for debugging|
| purposes only.                                                        |
\*---------------------------------------------------------------------*/
#ifndef _PRINT_ROUTES
#define _PRINT_ROUTES
void print_routes(_node *tour)
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
#endif
/*===========================================================================*/

/*--------------------------------------------------------------------*\
| This function computes the starter for a new route. It either returns|
| the farthest customer from the depot that is not yet on a route or it|
| returns a random node that is not yet on a route, depending on the   |
| value of the variable start.                                         |
\*--------------------------------------------------------------------*/
#ifndef _NEW_START
#define _NEW_START
int new_start(int *intour, heur_prob *p, int start, int num_cust)
{
  int starter = 0, start_pos, cust, count=0;
  int cost = -MAXINT, temp_cost;
  int vertnum = p->vertnum;

  if (start == FAR_INS)
    for (cust=1; cust<vertnum; cust++){
      if (((temp_cost = ICOST(&p->dist, 0, cust)) > cost) &&
	  (intour[cust] != IN_TOUR)){
	starter = cust;
	cost = temp_cost;
      }
    }
  else{
    start_pos = rand()%num_cust+1;
    for (cust = 1, count = 0; count<start_pos; cust ++)
      if (intour[cust] != IN_TOUR) count ++;
    starter = cust-1;
  }
  return(starter);
}
#endif
/*===========================================================================*/

/*---------------------------------------------------------------------*\
| find-max finds the cutomer with the maximum savings value among all   |
| customers not already on routes and returns that customer along with  |
| the position in which it should be inserted in the current route in   |
| order to achieve that savings.                                        |
\*---------------------------------------------------------------------*/

void find_max(int *ins_cust, int *savings, int *node1,
	      int *node2, _node *tour, int *intour,
	      int prev_route_end, heur_prob *p)
{
  int v0 = 0, v1;
  register int i;
  int vertnum = p->vertnum;

  *savings = -MAXINT;

  for (i = 1; i<vertnum; i++)
    if (intour[i] != IN_TOUR){
      v0 = 0;
      v1 = tour[prev_route_end].next;
      if (SAV(&p->dist, v0, v1, i) > *savings){
	*savings = (int) (SAV(&p->dist, v0, v1, i));
	*node1 = v0;
	*node2 = v1;
	*ins_cust = i;
      }
      do{
	v1 = tour[v0=v1].next;
	if (SAV (&p->dist, v0, v1, i) > *savings){
	  *savings = (int) (SAV(&p->dist, v0, v1, i));
	  *node1 = v0;
	  *node2 = v1;
	  *ins_cust = i;
	}
      }while (v1 != 0);
    }
  return;
}
  

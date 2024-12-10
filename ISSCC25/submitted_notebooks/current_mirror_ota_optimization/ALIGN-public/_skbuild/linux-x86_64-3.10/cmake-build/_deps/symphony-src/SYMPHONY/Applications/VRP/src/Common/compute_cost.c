/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* (c) Copyright 2000-2007 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

/* VRP include files */
#include "compute_cost.h"
#include "vrp_macros.h"
#include "vrp_const.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains functions for computing costs.
\*===========================================================================*/

/*===========================================================================*\
 * This function computes the cost of the edge from va to vb
\*===========================================================================*/

int compute_icost(distances *dist, int va, int vb)
{
  double q1, q2, q3, dx, dy, dz;
  int cost = 0;
	
  if (dist->wtype == _GEO){
    q1 = cos( dist->coordy[va] - dist->coordy[vb] );
    q2 = cos( dist->coordx[va] - dist->coordx[vb] );
    q3 = cos( dist->coordx[va] + dist->coordx[vb] );
    cost = (int) (RRR*acos(0.5*((1.0+q1)*q2-(1.0-q1)*q3))+1.0);
  }
  else{
    dx = dist->coordx[va] - dist->coordx[vb];
    dy = dist->coordy[va] - dist->coordy[vb];
    switch (dist->wtype){
      case _EUC_2D : cost = (int) floor( sqrt( dx*dx + dy*dy ) + 0.5);
		     break;
      case _EUC_3D : dz = dist->coordz[va] - dist->coordz[vb];
		     cost = (int) floor( sqrt( dx*dx + dy*dy + dz*dz) + 0.5);
		     break;
      case _MAX_2D : cost = (int) fabs(dx);
		     if (cost < fabs(dy)) cost = (int) fabs(dy);
		     break;
      case _MAX_3D : dz = dist->coordz[va] - dist->coordz[vb];
		     cost = (int) fabs(dx);
		     if (cost < fabs(dy)) cost = (int) fabs(dy);
		     if (cost < fabs(dz)) cost = (int) fabs(dz);
		     break;
      case _MAN_2D : cost = (int) floor( abs(dx)+abs(dy)+0.5 );
	             break;
      case _MAN_3D : dz = dist->coordz[va] - dist->coordz[vb];
                     cost = (int) floor( abs(dx)+abs(dy)+abs(dz)+0.5 );
                     break;
      case _CEIL_2D : cost = (int)ceil( sqrt( dx*dx + dy*dy ) + 0.5);
		      break;
      case _ATT     : cost = (int)( sqrt( (dx*dx + dy*dy ) / 10 ) + 1);
		      break;
    }
  }
  return( cost );
}

/*===========================================================================*\
 * This function computes the canonical tour and puts it into the field
 * p->cur_tour. It adds the nodes to routes in order until capacity is 
 * exceeded, and then it starts a new route,
\*===========================================================================*/

void canonical_tour(distances *dist, best_tours *cur_tour, int vertnum,
		    int capacity, int *demand)
{
  register int i, j = 1;
  int weight = 0;
  _node *tour = cur_tour->tour;

  if (demand[1] > capacity){
    fprintf(stderr, "Error: weight greater than truck capacity\n");
    exit(1); /*check whether any of the weights exceed capacity*/
  }

  tour[0].next = 1;
  tour[0].route = 0;

  for ( i=1; i < vertnum-1; i++){
    if (weight + demand[i] <= capacity){
      weight += demand[i];
      tour[i].next=i+1;        /*keep adding customers to routes until */
      tour[i].route=j;         /*capacity is exceeded*/
    }
    else{
      weight = demand[i];     /*start new route*/
      if (weight > capacity){
	fprintf(stderr, "Error: weight greater than truck capacity\n");
	exit(1);
      }
      j++;
      tour[i].next=i+1;
      tour[i].route=j;
    }
  }
  if (weight + demand[i] <= capacity){
    tour[i].next=0;
    tour[i].route=j;     /*add the final customer to the route and   */
  }                      /* mark the next customer as customer as the*/
  else{			 /*depot or start a new route as necessary   */
    weight = demand[i];
    if (weight > capacity){
      fprintf(stderr, "Error: weight greater than truck capacity\n");
      exit(1);
    }
    j++;
    tour[i].next=0;
    tour[i].route=j;
  }

  cur_tour->cost = compute_tour_cost (dist, tour);
  cur_tour->numroutes = j;
}

/*===========================================================================*\
 * This function computes the route information pertaining to a given 
 * tour. It just traces out the routes, counting the customers on each
 * route. When it reaches a new route,
 * it records the last cutomer on the previous route and the first
 * customer on the current route, and also the cost of the previous
 * route. It knows whether it has reached the end of a route by
 * checking whether the next customer has the same route number as it
 * does.
\*===========================================================================*/

int route_calc(distances *dist, _node *tour, int numroutes, 
	       route_data *route_info, int *demand)
{
  register int cur_node = 0;
  register int cur_route = 1;
  int cost = 0;

  for (cur_route = 1; cur_route<=numroutes; cur_route++){
    cur_node = tour[cur_node].next;
    route_info[cur_route].numcust++;
    route_info[cur_route].weight += demand[cur_node];
    route_info[cur_route].cost = ICOST(dist, 0, cur_node);
    route_info[cur_route].first = cur_node;
    while (tour[cur_node].route == tour[tour[cur_node].next].route){
      route_info[cur_route].cost += ICOST(dist, cur_node, tour[cur_node].next);
      cur_node = tour[cur_node].next;
      route_info[cur_route].numcust++;
      route_info[cur_route].weight += demand[cur_node];
    }
    route_info[cur_route].cost += ICOST(dist, 0, cur_node);
    route_info[cur_route].last = cur_node;
    cost += route_info[cur_route].cost;
  }
  return(cost);
}

/*===========================================================================*\
 * This function computes the cost of the tour held in
 * p->cur_tour. At the end of each route, it automatically
 * adds in the cost of returning to the depot and then
 * travelling back to the next customer.
\*===========================================================================*/

int compute_tour_cost(distances *dist, _node *tour)
{
  int cost=0;
  int v0, v1;

  for ( v1 = tour[0].next, cost = ICOST(dist, 0, tour[0].next);;){
    v1=tour[v0=v1].next;
    if (tour[v0].route == tour[v1].route)
      cost += ICOST(dist, v0, v1);
    else if (v1 == 0){
      cost += ICOST(dist, 0, v0);
      break;
    }
    else{
      cost += ICOST(dist, 0, v0);
      cost += ICOST(dist, 0, v1);
    }
  }

  return(cost);
}

double ECOST(double *cost, int v0, int v1, int vertnum)
{
   return((v0 < vertnum && v1 < vertnum) ? (cost[INDEX(v0, v1)]): 
	  ((v0 < vertnum && v0 > 0) ? (cost[INDEX(0, v0)]) : 
	   ((v1 < vertnum && v1 > 0) ? (cost[INDEX(0, v1)]): DEPOT_PENALTY)));
}

int ICOST(distances *dist, int v0, int v1)
{
   return(dist->wtype==_EXPLICIT ? dist->cost[INDEX(v0,v1)] :
	  compute_icost(dist,v0,v1));
}

int MCOST(distances *dist, int v0, int v1, int *lamda)
{
   return(dist->wtype==_EXPLICIT ?
	  dist->cost[INDEX(v0,v1)]+lamda[v0]+lamda[v1] :
	  (compute_icost(dist,v0,v1)+lamda[v0]+lamda[v1]));
}

int TCOST(distances *dist, int v0, int v1, int *lamda, int mu)
{
   return(v0 ? MCOST(dist, v0, v1, lamda) : MCOST(dist, v0, v1, lamda) - mu);
}


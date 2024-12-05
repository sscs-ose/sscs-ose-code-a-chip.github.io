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

#include "sweep.h"
#include "qsort.h"
#include <string.h>
#include <stdio.h>
/*-----------------------------------------------------------------------*\
| Make_tour receives the nodes in sorted order and performs the algorithm |
| described below, starting with a number of equally spaced nodes as      |
| determined by the parameter p->par.sweep_trials.                        |
\*-----------------------------------------------------------------------*/

void make_tour(heur_prob *p, sweep_data *data, best_tours *final_tour)
{
  int i, k, weight = 0, j=1, l;
  int interval, start=0;
  int cost;
  _node *tour;
  int *demand = p->demand;
  int vertnum = p->vertnum;
  int capacity = p->capacity;

  if (p->par.sweep_trials>vertnum - 1) p->par.sweep_trials = vertnum-1;

  final_tour->cost = MAXINT;

  tour = (_node *) calloc (vertnum, sizeof(_node));

  interval = vertnum/p->par.sweep_trials;

  for (l=0; l < p->par.sweep_trials; l++){

    tour[0].next = data[start].cust;
    tour[0].route = 0;

    for (k=1; k < vertnum-1; k++){

      i = (k-1) + start;
      if (i>vertnum-2) i-=(vertnum-1);
      
      if (weight + demand[data[i].cust] <= capacity){
	weight += demand[data[i].cust];
	if (i != vertnum - 2)
	  tour[data[i].cust].next = data[i+1].cust;
	else
	  tour[data[i].cust].next = data[0].cust;
	tour[data[i].cust].route=j;
      }
      else{
	weight = demand[data[i].cust];
	j++; if (i != vertnum - 2) tour[data[i].cust].next =
	data[i+1].cust; else tour[data[i].cust].next = data[0].cust;
	tour[data[i].cust].route=j; } } i = (k-1) + start; if
	(i>vertnum-2) i-=(vertnum-1); if (weight +
	demand[data[i].cust] <= capacity){ tour[data[i].cust].next =
	0; tour[data[i].cust].route = j; } else{
      j++;
      tour[data[i].cust].next = 0;
      tour[data[i].cust].route = j;
    }
    
    cost = compute_tour_cost (&p->dist, tour);
    if (cost < final_tour->cost){
      memcpy((char *)final_tour->tour,(char *)tour, vertnum*sizeof(_node));
      final_tour->cost = cost;
      final_tour->numroutes=j;
    }
    
    j=1;
    weight=0;
    start += interval;

  }
  free((char *)tour);
}

/*===========================================================================*/

/*-----------------------------------------------------------------*\
| The sweep algorithm is a very simple heuristic for clustering.    |
| We simply order the nodes radially about the depot and then add   |
| to the current route in this order until capacity is exceeded and |
| then we start a new route. Depending on where we start in the     |
| cyclic ordering, we get different solutions.                      |
\*-----------------------------------------------------------------*/

void sweep(int parent, heur_prob *p)
{
  printf("\nIn sweep....\n\n");
  int mytid, info, r_bufid;
  int i;
  int vertnum;
  sweep_data *data;
  float depotx, depoty;
  float tempx, tempy;
  double t=0;

  mytid = pvm_mytid();

  (void) used_time(&t);

  printf("mytid in sweep.c= %i", pvm_mytid());
  /*-----------------------------------------------------------------------*\
  |                     Receive the VRP data                                |
  \*-----------------------------------------------------------------------*/

  PVM_FUNC(r_bufid, pvm_recv(-1, SWEEP_TRIALS));
  PVM_FUNC(info, pvm_upkint(&(p->par.sweep_trials), 1, 1));
  printf("\nCheckpoint 1\n");
  /*-----------------------------------------------------------------------*/

  vertnum = p->vertnum;
  p->cur_tour = (best_tours *)calloc(1, sizeof(best_tours));
  p->cur_tour->tour = (_node *)calloc(vertnum, sizeof(_node));
  printf("\nCheckpoint 2\n");
  data = (sweep_data *)calloc(vertnum-1, sizeof(sweep_data));
  if (p->dist.coordx && p->dist.coordy){
     depotx = p->dist.coordx[0];
     depoty = p->dist.coordy[0];
     printf("\nCheckpoint 3\n");
     /*calculate angles for sorting*/
     for (i=0; i<vertnum-1; i++){
       tempx = p->dist.coordx[i+1] - depotx;
       tempy = p->dist.coordy[i+1] - depoty;
       data[i].angle = (float) atan2(tempy, tempx);
       if (data[i].angle < 0) data[i].angle += 2*M_PI;
       data[i].cust=i+1;
     }
     printf("\nCheckpoint 4\n");
     quicksort(data, vertnum-1);
     printf("\nCheckpoint 5\n");
     make_tour(p, data, p->cur_tour);
     printf("\nCheckpoint 6\n");
  /*-----------------------------------------------------------------------*\
  |               Transmit the tour back to the parent                      |
  \*-----------------------------------------------------------------------*/

     send_tour(p->cur_tour->tour, p->cur_tour->cost, p->cur_tour->numroutes,
	       SWEEP, used_time(&t), parent, vertnum, 0, NULL);
     printf("\nCheckpoint 7\n");
  }
  if (data) free((char *) data);
  printf("\nCheckpoint 8\n");    
  free_heur_prob(p);
  
}

  

    



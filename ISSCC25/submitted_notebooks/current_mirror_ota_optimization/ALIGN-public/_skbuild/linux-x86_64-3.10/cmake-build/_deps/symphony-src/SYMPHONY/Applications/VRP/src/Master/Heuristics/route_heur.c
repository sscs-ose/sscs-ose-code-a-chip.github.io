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
/* This software is licensed under the Common Public License. Please see     */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include <math.h>
#include <memory.h>
#include <string.h>
#include "BB_constants.h"
#include "BB_macros.h"
#include "sym_messages.h"
#include "vrp_const.h"
#include "route_heur.h"
#include "sym_timemeas.h"
#include <pvm3.h>
#include <stdio.h>
#include "compute_cost.h"
#include "sym_proccomm.h"
#include "heur_routines.h"
#include "receive_rout.h"
/*----------------------------------------------------------------------*\
| This program takes clusterings of nodes (determined by the initial     |
| solution which is given to the program) and tries to improve their     |
| routings using simple TSP heuristics such as far insert and near insert|
| For each cluster of customers, it takes the cheapest routing found by  |
| any of the heuristics and adds it to the tour to be sent back to the   |
| parent.                                                                |
\*----------------------------------------------------------------------*/

void route_heur(vrp_problem *vrp, heur_params *heur_par, 
	       heurs *rh, int trials,  int jobs,  int *tids, 
		int *sent, best_tours *solutions)
{

  int i, mintour = 0;
  int mytid, info, s_bufid, r_bufid, bytes, msgtag, parent;
  int cur_node, cur_route, numroutes;
  int pos, cost, last = 0;
  _node *tour;
  int mincost, temp_cost, temp, dummy = 0;
  route_data *route_info;
  double routing_time = 0, t=0;
  int round, index =0;
  (void) used_time(&t);
  best_tours *tours;
  heurs *ro;
  mytid = pvm_mytid();

  if (vrp->par.verbosity>1)
     printf("\nNow beginning routing heuristics ....\n\n");
 

  /*-----------------------------------------------------------------------*\
  |                   Initialize the heur_params data                       |
  \*-----------------------------------------------------------------------*/

  float fini_ratio = heur_par->fini_ratio;
  int ni_trials = heur_par->ni_trials;
  int fi_trials = heur_par->fi_trials;
  int fini_trials = heur_par->fini_trials;
  
  rh->tids = tids;
  rh->jobs = trials;//this indicates how many batches will run
 

  /*-----------------------------------------------------------------------*\
  |                     Initialize the starting tour                        |
  \*-----------------------------------------------------------------------*/

  for(round=0; round < rh->jobs; round++){/*---------------------------------*\
					  |in each round one batch is received| 
					  |a solution is synthesised and sent |
					  |to start_heur.                     |
					  \*---------------------------------*/
    ro = (heurs *)calloc(1, sizeof(heurs));
    ro->tids = tids;
    ro->jobs = fi_trials + fini_trials + ni_trials;
    vrp_problem *p = (vrp_problem *) calloc(1, sizeof(vrp_problem));
    memcpy((char *)p, (char *)vrp,sizeof(vrp_problem));
    p->edgenum = p->vertnum*(p->vertnum-1)/2;
    tours = p->cur_tour = (best_tours *) calloc (1, sizeof(best_tours));
    memcpy((char *)p->cur_tour, (char *)
	   &p->tours[p->tourorder[round%(p->tournum+1)]], sizeof(best_tours)) ;
    tour = p->cur_tour->tour = (_node *) calloc (p->vertnum, sizeof(_node));
    memcpy((char *)p->cur_tour->tour, (char *)p->
       tours[p->tourorder[round%(p->tournum+1)]].tour,p->vertnum*sizeof(_node)); 
    numroutes = tours->numroutes;
    tours->route_info =
    (route_data *) calloc (numroutes+1, sizeof(route_data));
    route_calc(&p->dist, tour, numroutes, tours->route_info, p->demand);

  /*--------------------------------------------------------------------*\
  | Here we broadcast the starting point rules to the various heuristics |
  | If there is only one trial of that particular heuristic, then we just|
  | use far insert as the starting point rule. For all the remaining     |
  | trials, we use random starting points.                               |
  \*--------------------------------------------------------------------*/
    /*round robin applied here*/
    temp = FAR_INS;
    if (fi_trials){
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkint(&dummy, 1, 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], S_FARTHEST_INS)); 
      sent[index%jobs]++;
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkbyte((char *)tours, sizeof(best_tours), 1));
      PVM_FUNC(info, pvm_pkbyte((char *)tour, (p->vertnum)*sizeof(_node), 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_FINS_VRP_DATA));
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkint(&temp, 1, 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_FINS_START_RULE));
      index++;
    }
    if (ni_trials){
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkint(&dummy, 1, 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], S_NEAREST_INS));
      sent[index%jobs]++;
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkbyte((char *)tours, sizeof(best_tours), 1));
      PVM_FUNC(info, pvm_pkbyte((char *)tour, (p->vertnum)*sizeof(_node), 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_NINS_VRP_DATA));
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkint(&temp, 1, 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_NINS_START_RULE));
      index++;
    }
    if (fini_trials){
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkint(&dummy, 1, 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], S_FARNEAR_INS));
      sent[index%jobs]++;
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkbyte((char *)tours, sizeof(best_tours), 1));
      PVM_FUNC(info, pvm_pkbyte((char *)tour, (p->vertnum)*sizeof(_node), 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_FNINS_VRP_DATA));
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkint(&temp, 1, 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_FNINS_START_RULE));
      PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
      PVM_FUNC(info, pvm_pkfloat(&fini_ratio, 1, 1));
      PVM_FUNC(info, pvm_send(tids[index%jobs], FINI_RATIO));
      index++;
    }
    temp = MAX(fi_trials, ni_trials);
    temp = MAX(temp, fini_trials);
    for (i=1; i<temp; i++){
      if (fi_trials>i){
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkint(&dummy, 1, 1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], S_FARTHEST_INS)); 
	sent[index%jobs]++;
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkbyte((char *)tours, sizeof(best_tours), 1));
	PVM_FUNC(info, pvm_pkbyte((char *)tour, (p->vertnum)*sizeof(_node),1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_FINS_VRP_DATA));
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkint(&p->par.rand_seed[(i-1)%NUM_RANDS], 1, 1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_FINS_START_RULE));
	index++;
      }
      if (ni_trials>i){
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkint(&dummy, 1, 1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], S_NEAREST_INS));
	sent[index%jobs]++;
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkbyte((char *)tours, sizeof(best_tours), 1));
	PVM_FUNC(info, pvm_pkbyte((char *)tour, (p->vertnum)*sizeof(_node),1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_NINS_VRP_DATA));
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkint(&p->par.rand_seed[(i-1)%NUM_RANDS], 1, 1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_NINS_START_RULE));
	index++;
      }
      if (fini_trials>i){
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkint(&dummy, 1, 1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], S_FARNEAR_INS));
	sent[index%jobs]++;
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkbyte((char *)tours, sizeof(best_tours), 1));
	PVM_FUNC(info, pvm_pkbyte((char *)tour, (p->vertnum)*sizeof(_node),1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_FNINS_VRP_DATA));
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkint(&p->par.rand_seed[(i-1)%NUM_RANDS], 1, 1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], ROUTE_FNINS_START_RULE));
	PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
	PVM_FUNC(info, pvm_pkfloat(&fini_ratio, 1, 1));
	PVM_FUNC(info, pvm_send(tids[index%jobs], FINI_RATIO));
	index++;
      }
    }

  /*-----------------------------------------------------------------------*\
  |         Receive the tours back from the processes                       |
  |   [initialize the p->tours[i], and then receive into it]                |
  \*-----------------------------------------------------------------------*/

    tours = p->tours = 
      (best_tours *) calloc (p->par.tours_to_keep, sizeof(best_tours));
    tours[0].cost = MAXINT;
    tours[0].tour = (_node *) malloc ((int)p->par.tours_to_keep * p->vertnum
				    * sizeof(_node));
    for (pos=1; pos<p->par.tours_to_keep; pos++){
      tours[pos].tour = p->tours[pos-1].tour + p->vertnum;
      tours[pos].cost = MAXINT;
    }
    p->tourorder = (int *) calloc((int)p->par.tours_to_keep+1,
					    sizeof(int));

    routing_time = receive_tours(p, ro, &last, TRUE, TRUE, FALSE, FALSE, 
				 jobs, sent);

  /*-----------------------------------------------------------------------*\
  |               Form the final tour                                       |
  \*-----------------------------------------------------------------------*/

  /*--------------------------------------------------------------------*\
  | This section of the program compares all the routings for a          |
  | particular cluster and chooses the best one to be in the final       |
  | solution.                                                            |
  \*--------------------------------------------------------------------*/
    route_info = p->cur_tour->route_info;

    cost = 0;
    cur_node = 0;
    for (cur_route=1; cur_route<=numroutes; cur_route++){
      mincost = MAXINT;
      //choose the mincost tour for the current route as mintour.
      for (i = 0; i<=p->tournum; i++)
	if ((temp_cost = tours[i].route_info[cur_route].cost) < mincost){
	  mincost = temp_cost;
	  mintour = i;
	}
      //if that is cheaper than current tour's current route
      if (mincost < route_info[cur_route].cost){
	//then append that route to current tour's current node.
	tour[cur_node].next = tours[mintour].route_info[cur_route].first;
	do{
	  //update current node.
	  cur_node = tour[cur_node].next;
	  tour[cur_node].next = tours[mintour].tour[cur_node].next;
	}while(cur_node != tours[mintour].route_info[cur_route].last);
	cost += tours[mintour].route_info[cur_route].cost;
      }
      else{
	tour[cur_node].next = route_info[cur_route].first;
	cost += route_info[cur_route].cost;
	cur_node = route_info[cur_route].last;
      }
    }
    printf("\nFinal tour ready.\n\n");
  /*-----------------------------------------------------------------------*\
  |                       Store the final tour                              |
  \*-----------------------------------------------------------------------*/
 
    solutions[round].tour = (_node *) calloc (p->vertnum, sizeof(_node));
    memcpy((char *)solutions[round].tour, (char *)tour, p->vertnum*sizeof(_node));     
    solutions[round].cost = cost;
    solutions[round].numroutes = numroutes;
    solutions[round].solve_time = used_time(&t)+routing_time;
    solutions[round].algorithm = p->cur_tour->algorithm;

    if (p->tourorder) free ((int *) p->tourorder);			  
    if (p->cur_tour->tour) free((_node *) p->cur_tour->tour);
    if (p->cur_tour->route_info) free ((route_data *) p->cur_tour->route_info);
    if (p->cur_tour) free ((best_tours *) p->cur_tour);
    if (p->tours) free ((best_tours *) p->tours);
    if(p) free ((vrp_problem *) p);
    if (ro) free((char *) ro);
  }// for(round=0; round < rh->jobs; round++)
}
 
  







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

#include <stdio.h>
#include <memory.h>
#include <stdlib.h>

#include "exchange_heur.h"
#include "vrp_master_functions.h"
#include "vrp_const.h"
#include "sym_proccomm.h"

void exchange_heur(vrp_problem *vrp, heurs *eh, int trials, int jobs, 
		   int which, int *tids, int *sent)
{
  int i, info, dummy;
  int s_bufid;
  _node *tour;
  best_tours tours;

  if (vrp->par.verbosity >1){
     if (which == FIRST_SET)
	printf("\nNow beginning first set of exchange heuristics ....\n\n");
     else if (which == SECOND_SET)
	printf("\nNow beginning second set of exchange heuristics ....\n\n");
  }

  eh->tids = tids;
  eh->jobs = trials;

  if (trials)    
    for (i=0; i < eh->jobs; i++){
    PVM_FUNC(s_bufid, pvm_initsend(PvmDataRaw));
    PVM_FUNC(info, pvm_pkint(&dummy, 1, 1));
    PVM_FUNC(info, pvm_send(tids[i%jobs], which ? S_EXCHANGE : S_EXCHANGE2));
    sent[i%jobs]++;
    }

  if (jobs == 0){
    fprintf(stderr, "\nNo jobs started... \n\n");
    return;
  }
  else if (vrp->par.verbosity >2)
     printf("\n%i jobs started ....\n\n", jobs);


  /*-----------------------------------------------------------------------*\
  |                  Broadcast data to the processes                        |
  \*-----------------------------------------------------------------------*/

  //data is already sent by start_heurs.c

  /*-----------------------------------------------------------------------*\
  |                  Broadcast best tours to the processes                  |
  \*-----------------------------------------------------------------------*/

  for (i=0; i<eh->jobs; i++){
    s_bufid = init_send(DataInPlace);
    tours = vrp->tours[vrp->tourorder[i%(vrp->tournum+1)]];
    tour = tours.tour;
    send_char_array((char *)&tours, sizeof(best_tours));
    send_char_array((char *)tour, (vrp->vertnum)*sizeof(_node));
    send_msg(tids[i%jobs],EXCHANGE_HEUR_TOUR);
  }
}



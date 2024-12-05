/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/* This file was written by Ali Pilatin January, 2005 (alp8@lehigh.edu)      */
/*                                                                           */
/* (c) Copyright 2000-2005 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#include "vrp_heurs.h"
#include "heur_routines.h"
#include <stdio.h>

int main (int argc, char **argv)
{
  int  r_bufid, info, bytes, msgtag, parent, endofprocess = 0;
  heur_prob *p = (heur_prob *) calloc(1, sizeof(heur_prob));
  parent = receive(p);
  printf("\nWelcome, I am task %i\n\n", pvm_mytid());
  while(!endofprocess){
    printf("\nim gonna try to receive at parallel_process.\n");
    PVM_FUNC(r_bufid, pvm_recv(-1, -1));
    PVM_FUNC(info, pvm_bufinfo(r_bufid, &bytes, &msgtag, &parent));
    printf("\nim still in parallel_process\n");
    switch(msgtag){

    case S_EXCHANGE:
      exchange(parent, p);
      break;

    case S_EXCHANGE2:
      exchange2(parent, p);
      break;

    case S_FARNEAR_INS:
      farnear_ins(parent, p);
      break;

    case S_FARTHEST_INS:
      farthest_ins(parent, p);
      break;

    case S_MST:
      mst();
      break;

    case S_NEAREST_INS:
      nearest_ins(parent, p);
      break;

    case S_NEAR_CLUSTER:
      near_cluster(parent, p);
      break;

    case S_SAVINGS:
      savings(parent, p);
      break;

    case S_SAVINGS2:
      savings2(parent, p);
      break;

    case S_SAVINGS3:
      savings3(parent, p);
      break;

    case S_SWEEP:
      sweep(parent, p);
      break;

    case S_TSP_FI:
      tsp_fi(parent, p);
      break;

    case S_TSP_FINI:
      tsp_fini(parent, p);
      break;

    case S_TSP_NI:
      tsp_ni(parent, p);
      break;

    case STOP:
      endofprocess = 1;
      
    }
  }
  return 0;
}

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

#include <memory.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cluster_heur.h"
#include "vrp_master_functions.h"
#include "vrp_const.h"
#include "sym_proccomm.h"
#include "BB_macros.h"


/*===========================================================================*/

void generate_starter(int vertnum, int *starter, int num)
{
   int i, rans = 0,  pos = 0;
   int ran;
   
   for (i = 0; i < num; i++){
      do{
	 ran = (RANDOM() % vertnum) + 1;//draw a random vertex
	 for (pos = 0; pos < rans; pos++)
	    if (starter[pos] == ran) break;
      }while (pos < rans);//continue drawing till a new vertex is drawn

      starter[rans++] = ran;/*---------------------------------*\
                            | assign this vertex to the current |
			    | position, go back and draw a      |
			    | vertex for the next position      |
			    \*---------------------------------*/
   }
}

/*===========================================================================*/

/*----------------------------------------------------------------------*\
| This function spawns the various cluster heuristics which are the first|
| step in the process of finding reasonable upper bounds                 |
\*----------------------------------------------------------------------*/

void cluster_heur(vrp_problem *vrp, heur_params *heur_par,
		  heurs *ch, int trials, int jobs, int *tids, int *sent)
{
  vrp_params *par = &vrp->par;
  
  int *sweep_tid, *savings_tid, *savings2_tid, *near_cluster_tid, *temp_tid;
  int *tsp_ni_tid, *tsp_fi_tid, *tsp_fini_tid, *savings3_tid;
  int sweep_job=0, savings_jobs=0;
  int savings2_jobs = 0, savings3_jobs = 0, near_cluster_job=0;
  int tsp_ni_jobs = 0, tsp_fi_jobs = 0, tsp_fini_jobs = 0;
  int i, temp, dummy;
  int s_bufid;
  int vertnum = vrp->vertnum;
  float lamda, mu;
  float temp_mu, temp_lamda;
  float lamda_int, mu_int;
  int grid_size, count = 0, j, l;
  int start;
  int farside = (int) (vertnum * heur_par->fini_ratio);
  int *starter;
  int sw_index = 0, tni_index=0, tfi_index=0; 
  int tfini_index=0, s_index=0, s2_index=0, s3_index=0; 


  if (vrp->par.verbosity > 1)
  printf("\nNow beginning cluster heuristics ....\n\n");

  /*-----------------------------------------------------------------------*\
  |                        Enlisting this process                           |
  \*-----------------------------------------------------------------------*/

  if (jobs == 0){
     fprintf(stderr, "\nNo jobs started... \n\n");
     return;
  }
  else if (vrp->par.verbosity > 2)
     printf("\n%i jobs started ....\n\n", jobs);

  ch->tids = tids;
  ch->jobs = trials;
  
 
  /*-----------------------------------------------------------------------*\
  |         Broadcast number of trials to sweep and tsp routines            |
  \*-----------------------------------------------------------------------*/
  sw_index = 0;
  if ((heur_par->sweep_trials)&&(vrp->dist.wtype)){
    s_bufid = init_send(DataInPlace);
    send_int_array(&dummy, 1);
    send_msg(tids[sw_index%jobs], S_SWEEP);
    s_bufid = init_send(DataInPlace);
    send_int_array(&heur_par->sweep_trials, 1);
    send_msg(tids[sw_index%jobs], SWEEP_TRIALS);
    sent[sw_index]++;
    sw_index++;
    printf("\nmessage sent\n\n");
   }

  for(tni_index=sw_index; tni_index<sw_index+heur_par->tsp.ni_trials; tni_index++){
      s_bufid = init_send(DataInPlace); 
      send_int_array(&dummy, 1);
      send_msg(tids[tni_index%jobs], S_TSP_NI);
      sent[tni_index%jobs]++;
      s_bufid = init_send(DataInPlace);
      send_int_array(&heur_par->tsp.num_starts, 1);
      send_msg(tids[tni_index%jobs], TSP_NI_TRIALS);
  }
  for(tfi_index=tni_index; tfi_index<tni_index+heur_par->tsp.fi_trials; 
      tfi_index++){
      s_bufid = init_send(DataInPlace); 
      send_int_array(&dummy, 1);
      send_msg(tids[tfi_index%jobs], S_TSP_FI);
      sent[tfi_index%jobs]++;
      s_bufid = init_send(DataInPlace);
      send_int_array(&heur_par->tsp.num_starts, 1);
      send_msg(tids[tfi_index%jobs], TSP_FI_TRIALS);
  }
  for(tfini_index=tfi_index; tfini_index<tfi_index+heur_par->tsp.fini_trials; 
      tfini_index++){
      s_bufid = init_send(DataInPlace); 
      send_int_array(&dummy, 1);
      send_msg(tids[tfini_index%jobs], S_TSP_FINI);
      sent[tfini_index%jobs]++;
      s_bufid = init_send(DataInPlace);
      send_int_array(&heur_par->tsp.num_starts, 1);
      send_msg(tids[tfini_index%jobs], TSP_FINI_TRIALS);
      s_bufid = init_send(DataInPlace);
      send_int_array(&farside, 1);
      send_msg(tids[tfini_index%jobs], TSP_FINI_RATIO);
  }
 
  //no need to start saving and saving2 here yet, since no data is sent.

  if (heur_par->savings3_par.grid_size &&
      heur_par->savings3_par.savings_trials &&
      (vrp->numroutes ||
       (!vrp->numroutes && vrp->dist.coordx && vrp->dist.coordy)))
    for(s3_index=tfini_index; s3_index<tfini_index+
	  heur_par->savings3_par.grid_size*
	  heur_par->savings3_par.grid_size; s3_index++){
      s_bufid = init_send(DataInPlace); 
      send_int_array(&dummy, 1);
      send_msg(tids[s3_index%jobs], S_SAVINGS3);    
      sent[s3_index%jobs]++;
      s_bufid = init_send(DataInPlace);
      send_int_array(&vrp->numroutes, 1);
      send_msg(tids[s3_index%jobs], S3_NUMROUTES);
      //sending savings3 parameters below.
      grid_size = heur_par->savings3_par.grid_size;
      lamda = heur_par->savings3_par.lamda;
      mu = heur_par->savings3_par.mu;
      if (grid_size == 1){
	lamda_int = 0;
	mu_int = 0;
      }
      else{
	lamda_int = ((float)lamda)/((float)(grid_size - 1));
	mu_int = ((float)mu)/((float)(grid_size -1));
      }
      for (i=0; i < grid_size; i++){
	temp_lamda = i * lamda_int;
	if (i == grid_size-1) temp_lamda = (float) lamda; 
	for (j=0; j < grid_size; j++){
	   temp_mu = j * mu_int;
	   if (j == grid_size-1) temp_mu = (float) mu; 
	   s_bufid = init_send(DataInPlace);
	   send_float_array(&temp_mu, 1);
	   send_float_array(&temp_lamda, 1);
	   send_int_array(&start, 1);
	   send_msg(tids[s3_index%jobs], SAVINGS3_DATA);
	   //count++;
	   if (count > savings3_jobs) break;
	}
	if (count > savings3_jobs) break;
      }
    }

  if (heur_par->near_cluster_trials &&
      (vrp->numroutes ||
       ((!vrp->numroutes) && (vrp->dist.wtype)))){
      s_bufid = init_send(DataInPlace); 
      send_int_array(&dummy, 1);
      send_msg(tids[s3_index%jobs], S_NEAR_CLUSTER);    
      sent[s3_index%jobs]++;
      s_bufid = init_send(DataInPlace);
      send_int_array(&vrp->numroutes, 1);
      send_msg(tids[s3_index%jobs], NC_NUMROUTES);
  }
   // Above,  msg for cluster heuristic sent to the next available process

  /*------------------------------------------------------------------------*\
  |           Generate the random starting points and broadcast              |
  \*------------------------------------------------------------------------*/
  SRANDOM(vrp->par.rand_seed[0]);
  heur_par->tsp.ni_trials = MIN(heur_par->tsp.ni_trials, vertnum);
  heur_par->tsp.fi_trials = MIN(heur_par->tsp.ni_trials, vertnum);
  heur_par->tsp.fini_trials = MIN(heur_par->tsp.ni_trials, vertnum);
  starter = ch->starter = 
     (int *) calloc (heur_par->tsp.ni_trials + heur_par->tsp.fi_trials +
		     heur_par->tsp.fini_trials, sizeof(int));
  generate_starter(vertnum-1, starter, heur_par->tsp.ni_trials);
  generate_starter(vertnum-1, starter + heur_par->tsp.ni_trials,
		   heur_par->tsp.fi_trials);
  generate_starter(vertnum-1, starter + heur_par->tsp.ni_trials +
		   heur_par->tsp.fi_trials, heur_par->tsp.fini_trials);
  if (heur_par->tsp.ni_trials)                //here, vertnum variable//
     starter[0] = vertnum;                    //is sent to each tsp   //
  if (heur_par->tsp.fi_trials)                //heuristic as the first//
     starter[tni_index] = vertnum;            //message.              //
  if (heur_par->tsp.fini_trials)              /////////////////////////
     starter[tfi_index] = vertnum;
  
  for (i=0; i< heur_par->tsp.ni_trials+heur_par->tsp.fi_trials
	 +heur_par->tsp.fini_trials; i++){
     s_bufid = init_send(DataInPlace);
     send_int_array(starter+i, 1);
     send_msg(tids[(i+sw_index)%jobs], TSP_START_POINT);
  }
  
  /*-----------------------------------------------------------------------*\
  |                Broadcast parameters to savings                          |
  \*-----------------------------------------------------------------------*/
  
  /*--------------------------------------------------------------------*\
  | Here is where the parameter settings are given to the various        |
  | savings proceses. The parameters mu and lamda from the parameter     |
  | file indicate maximum values for these particular parameters. Then   |
  | depending on the grid-size that is specified, I partition the        |
  | square (0, mu) X (0, lamda) into a grid and send various             |
  | combinations of parameters to the various processes. Also, I give    |
  | the processes different starting point rules. If I send FAR_INS to   |
  | a process, then the frathest customer from the depot is always       |
  | used to intialize new routes. Otherwise, I send a random seed that   |
  | can be used to randonly select the next customer to be added to a    |
  | route. The first "block" of trials receives the FAR_INS signal.      |
  | The remaining blocks, launched if savings_trials >1, receive         |
  | random seeds                                                         |
  \*--------------------------------------------------------------------*/

 if (heur_par->savings_par.grid_size && heur_par->savings_par.savings_trials){
     temp_tid = savings_tid;
     grid_size = heur_par->savings_par.grid_size;
     lamda = heur_par->savings_par.lamda;
     mu = heur_par->savings_par.mu;
     if (grid_size == 1){
	lamda_int = 0;
	mu_int = 0;
     }
     else{
       lamda_int = ((float)lamda)/((float)(grid_size - 1));//lambda interval
       mu_int = ((float)mu)/((float)(grid_size -1));//mu interval
     }
     for (l=0; l<heur_par->savings_par.savings_trials; l++){
	switch(l){
	 case 0: start = FAR_INS;
	   break;  /*send FAR_INS rule to the first "block"*/
	 default: start = vrp->par.rand_seed[(l-1)%6];
	}   /*send random seeds to the remaining blocks*/
	for (i=0; i < grid_size; i++){
	   temp_lamda = i * lamda_int;
	   if (i == grid_size-1) temp_lamda = (float) lamda; 
	   for (j=0; j < grid_size; j++){
	      temp_mu = j * mu_int;
	      if (j == grid_size-1) temp_mu = (float) mu; 
	      s_bufid = init_send(DataInPlace); 
	      send_int_array(&dummy, 1);
	      send_msg(tids[(s3_index+1+count)%jobs], S_SAVINGS);
	      sent[(s3_index+1+count)%jobs]++;
	      s_bufid = init_send(DataInPlace);
	      send_float_array(&temp_mu, 1);
	      send_float_array(&temp_lamda, 1);
	      send_int_array(&start, 1);
	      send_msg(tids[(s3_index+1+count)%jobs], SAVINGS_DATA);
	      count++;
	      if (count > heur_par->savings_par.savings_trials) break;
	   }
	   if (count > heur_par->savings_par.savings_trials) break;
	}
     }
 }

             /*This is the same as above except for savings2 instead *\
	     \*of savings.                                           */
 if (heur_par->savings_par.grid_size && heur_par->savings_par.savings2_trials){
     temp_tid = savings2_tid;
     grid_size = heur_par->savings_par.grid_size;
     lamda = heur_par->savings_par.lamda;
     mu = heur_par->savings_par.mu;
     if (grid_size == 1){
	lamda_int = 0;
	mu_int = 0;
     }
     else{
	lamda_int = ((float)lamda)/((float)(grid_size - 1));
	mu_int = ((float)mu)/((float)(grid_size -1));
     }
     for(l = 0; l < heur_par->savings_par.savings2_trials; l++){
	switch(l){
	 case 0: start = FAR_INS;
	   break;
	 default: start = vrp->par.rand_seed[(l-1)%6];
	}
	for (i = 0; i < grid_size; i++){
	   temp_lamda = i * lamda_int;
	   if (i == grid_size-1) temp_lamda = (float) lamda; 
	   for (j = 0; j < grid_size; j++){
	      temp_mu = j * mu_int;
	      if (j == grid_size-1) temp_mu = (float) mu; 
	      s_bufid = init_send(DataInPlace); 
	      send_int_array(&dummy, 1);
	      send_msg(tids[(s3_index+1+count)%jobs], S_SAVINGS2);
	      sent[(s3_index+1+count)%jobs]++;
	      s_bufid = init_send(DataInPlace);
	      send_float_array(&temp_mu, 1);
	      send_float_array(&temp_lamda, 1);
	      send_int_array(&start, 1);
	      send_msg(tids[(s3_index+1+count)%jobs], SAVINGS2_DATA);
	      count++;
	      if (count > savings2_jobs) break;
	   }
	   if (count > savings2_jobs) break;
	}
     }
 }
}



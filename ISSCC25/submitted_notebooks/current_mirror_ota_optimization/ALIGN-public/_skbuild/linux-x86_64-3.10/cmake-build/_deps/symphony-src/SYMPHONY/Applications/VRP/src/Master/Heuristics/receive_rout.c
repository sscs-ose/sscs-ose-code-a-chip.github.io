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
#include <time.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include "BB_constants.h"
#include "sym_messages.h"
#include "receive_rout.h"
#include "compute_cost.h"
#include "vrp_master_functions.h"
#include "network.h"
#include "sym_proccomm.h"
#include "vrp_const.h"
#include "vrp_macros.h"

/*--------------------------------------------------------------------*\
| The receive_tours function is used to receive the tours              |
| output by various heuristic processes running in parallel and keep   |
| an ordered list of them in a binary tree. It checks about once every |
| second to see if any tours have come into the recieve buffer and if  |
| so, it updates the binary tree and stores the tour if it is one of   |
| the lowest (vrp->par.tours_to_keep) cost tours                       |
\*--------------------------------------------------------------------*/

double receive_tours(vrp_problem *vrp, heurs *hh, int *last,
		     char print, char routes, char add_edges,
		     char win, int jobs, int *sent)
{
   int pos;
   int i, low_run, dead_tasks = 0;
   int s_bufid = 0, r_bufid = 0, bytes, msgtag, tid;
   _node *tour;
   int *tourorder = vrp->tourorder, tournum = -1;
   best_tours *tours = vrp->tours;/*-------------------------------------*\
				  | new best tours are put in this tours* |
				  \*-------------------------------------*/
   int cost;
   int numroutes, v0, v1, vertnum = vrp->vertnum;
   route_data *route_info = NULL;
   time_t cur_time, prev_time;
   int algorithm;
   double solve_time = 0, total_solve_time = 0;
   edge_data *next_edge = NULL;
   small_graph *g = NULL;
   int newedgenum=0, round =0, round1 = 0;
   int receive = 1, *returned, some_returned = 0;
   int mytid = pvm_mytid();
   if (add_edges){
      g = vrp->g;
      next_edge = g->edges+g->edgenum;
   }
   
   if (hh->jobs == 0) return((double) 0);

   returned= (int *) calloc(jobs+1, sizeof(int));   
   tour = (_node *) calloc (vertnum, sizeof(_node));
   
   time(&prev_time);
   
   while(receive){
     receive = 0;
     r_bufid = nreceive_msg(-1, -1); 
     if (r_bufid){           /*check buffer for tour*/
       bufinfo(r_bufid, &bytes, &msgtag, &tid);//get the tid of buffer
       for (i=0; hh->tids[i] != tid; i++);//find the corresponding tids[i]
       returned[i] += 1;
       receive_char_array((char *)tour, (vertnum)*sizeof(_node));//receive a tour
       receive_int_array(&cost, 1);  
       receive_int_array(&numroutes, 1); /*receive
					   tour */
       receive_int_array(&algorithm, 1);
       receive_dbl_array(&solve_time, 1);
       if (routes){
	 route_info = (route_data *) calloc(numroutes + 1,
					    sizeof(route_data));
	 receive_char_array((char *)route_info, (numroutes+1) *
			    sizeof(route_data));

       }
       if (!cost){ /*zero cost is an error flag - don't store this tour*/
	 if (vrp->par.verbosity >2)
	   fprintf(stderr, "Error receiving job %i - infeasible\n", i+1);
	 if (win && vrp->par.verbosity>4){
	   if(!vrp->dg_id){
	     /*vrp->window = init_win(vrp->par.executables.winprog,
	       vrp->par.debug.winprog,
	       vrp->posx, vrp->posy, vrp->vertnum);*/
	   }
	   /*vrp->window->windata.draw = TRUE;
	     disp_tour(vrp->window, tour, TRUE);*/
	 }
	 hh->jobs--;
	 if (!hh->jobs) return((double) 0);
	 else continue;
       }
       if (tournum + 1 < vrp->par.tours_to_keep){
	 *last = ++tournum;
	 tours[*last].cost = MAXINT;
       }
       else{
	 *last = tourorder[tournum];
       }
       if (tours[*last].cost >cost){ /*check to see if tour is one of *\
				     |the (vrp->par.tours_to_keep)     |
				     |cheapest and if so, update       |
				     \*binary tree                    */
	 tours[*last].cost = cost;
	 tours[*last].numroutes = numroutes;
	 tours[*last].algorithm = algorithm;
	 tours[*last].solve_time += solve_time;
	 total_solve_time += solve_time;
	 if(routes)
	   tours[*last].route_info = route_info;
	 memcpy((char *)tours[*last].tour, (char *)tour,
		vertnum*sizeof(_node));
	 for (pos = tournum -1;
	      pos >=0 &&tours[tourorder[pos]].cost >cost; pos--){
	   tourorder[pos+1]=tourorder[pos];
	 }
	 tourorder[pos+1]=*last;
       }
       
       if (print && vrp->par.verbosity >2){
	 printf("A job from task %i returned: cost = %i trucks = %i", hh->tids[i],
		cost, numroutes);
	 printf(" algorithm = %i solution time = %.3f\n", algorithm,
		solve_time);
	 
	    
	 if (vrp->par.verbosity>4 && win){
	   if(!vrp->dg_id){
	     /*vrp->window = init_win(vrp->par.executables.winprog,
	       vrp->par.debug.winprog,
	       vrp->posx, vrp->posy, vrp->vertnum);*/
	       }
	   /*vrp->window->windata.draw = TRUE;
	     disp_tour(vrp->window, tour, TRUE);*/
	   /*display the tour in the tour window*/
	 }
       }
       if (add_edges){
	 v0 = 0;
	 v1 = tour[0].next;
	 for (pos = 0; pos<vertnum; pos++){
	   v1 = tour[v0=v1].next;
	   if(tour[v0].route == tour[v1].route){
	     if (v0 < v1){
	       next_edge->v0 = v0;
	       next_edge->v1 = v1;
	     }
	     else{
	       next_edge->v0 = v1;
	       next_edge->v1 = v0;
	     }
	     if (!bsearch((char *)next_edge, (char *)g->edges,
			  g->edgenum, sizeof(edge_data), is_same_edge)){
	       (next_edge++)->cost = ICOST(&vrp->dist, v0, v1);
	       newedgenum++;
	     }
	   }
	 }
       }
       time(&prev_time); /*reset the time_out timer*/
     }
     else{
#if 0
	 sleep(.01); /*the purpose of this sleep command is to keep the     *\
		     | program from checking the buffer continuously, which  |
		     | chews up CPU time. Before continuing, there is a      |
		     | check to see if too much time has elapsed since the   |
		     | last tour was received and if so all remaining        |
		     \*processes are killed and the function terminates     */
#endif
	 time (&cur_time);
	 if (cur_time > prev_time + vrp->par.time_out.ub){ 
	   if (vrp->par.verbosity>1)
	     printf("\nReceive tours timed out after %i seconds ...\n",
		    vrp->par.time_out.ub);
	   break;
	 }
     }
     for(i=0; i < jobs; i++){
       if((returned[i] != sent[i]) && (pstat(hh->tids[i]) == PROCESS_OK)){
	 receive = 1;
	 break;//break out of loop
       }      
     }
   } 
   if (add_edges && newedgenum){
      g->edgenum += newedgenum;
      delete_dup_edges(g);
   }
   vrp->tournum = tournum;
   for (i=0; i<jobs; some_returned+=returned[i],i++);
   if ((print) && (some_returned)){
      if (vrp->par.verbosity >2){
	 printf("\nTotal solution time for heuristics in this "
		"batch is %.3f\n\n", total_solve_time);
	 printf("the best tour values: \n");
	 for (pos=0; pos<=tournum; pos++)
	    printf("%i algorithm = %i\n", tours[tourorder[pos]].cost,
		   tours[tourorder[pos]].algorithm);
	 if (add_edges)
	    printf("\nNumber of edges in the problem is %i\n\n", g->edgenum);
      }
      else if (vrp->par.verbosity >1){
	 printf("Best tour found has cost %i with %i trucks using "
		"algorithm %i\n",
		tours[tourorder[0]].cost, tours[tourorder[0]].numroutes,
		tours[tourorder[0]].algorithm);
	 printf("Total solution time for this solution is %.3f\n",
		tours[tourorder[0]].solve_time);
	 printf("Total solution time for heuristics in this batch is %.3f\n\n",
		total_solve_time);
	 if (add_edges)
	    printf("Number of edges in the problem is %i\n\n", g->edgenum);
      }
   }
   if (tour) free ((char *) tour);
   if (hh->starter) free((char *)hh->starter);
   hh->starter = NULL;
   if (returned) free((char *)returned);
   for(i=0; i<jobs; sent[i]=0, i++);
   return(total_solve_time);
}

/*===========================================================================*/

double receive_lbs(vrp_problem *vrp, heurs *hh, char win, 
		   int numroutes, int jobs, int *sent)
{
   int i, low_run, dead_tasks = 0, nr = numroutes;
   int r_bufid = 0, bytes, msgtag, tid, s_bufid;
   int *tree, *temp_tree;
   edge_data *best_edges, *temp_best_edges;
   int cost, round =0;
   time_t cur_time, prev_time;
   double solve_time = 0, total_solve_time = 0;
   int receive, *returned, some_returned = 0;   
   if (hh->jobs == 0) return((double) 0);
   returned= (int *) calloc(jobs+1, sizeof(int));   
   tree = vrp->lb->tree = (int *) calloc(vrp->vertnum, sizeof(int));
   best_edges = vrp->lb->best_edges = (edge_data *) calloc(numroutes,
							   sizeof(edge));
   temp_tree =  (int *) calloc (vrp->vertnum, sizeof(int));
   temp_best_edges = vrp->lb->best_edges = (edge_data *) calloc(numroutes,
								sizeof(edge));
   vrp->lb->lower_bound = (double) -MAXINT;
   
   time(&prev_time);
   while(receive){
     receive = 0;
      r_bufid = nreceive_msg(-1, LOWER_BOUND); 
      if (r_bufid){           /*check buffer for tour*/
	 bufinfo(r_bufid, &bytes, &msgtag, &tid);
	 for (i=0; hh->tids[i] != tid; i++);
	 returned[i] += 1;
	 receive_int_array(temp_tree, vrp->vertnum);
	 receive_char_array((char *)temp_best_edges,
			    numroutes * sizeof(edge_data));
	 receive_int_array(&cost, 1);
	 receive_dbl_array(&solve_time, 1);
	 total_solve_time += solve_time;
	 if ((double) cost > vrp->lb->lower_bound){
	    vrp->lb->lower_bound = (double) cost;
	    memcpy (tree, temp_tree, vrp->vertnum*sizeof(int));
	    memcpy (best_edges, temp_best_edges, numroutes*sizeof(edge));
	 }
	 
	 if (!win && vrp->par.verbosity>2){
	    switch(i){
	     case 0: 
	       printf("A job from 1st task returned: cost = %i trucks = %u "
		      "solution time = %.3f\n", cost, nr, solve_time);
	       break;
	     case 1:
	       printf("A job from 2nd task returned: cost = %i trucks = %u "
		      "solution time = %.3f\n", cost, nr, solve_time);
	       break;
	     case 2:
	       printf(
		      "A job from 3rd task returned: cost = %i trucks = %u "
		      "solution time = %.3f\n", cost, nr, solve_time);
	       break;
	     default:
	       printf("A job from %ith task returned: cost = %i trucks = %u "
		      "solution time = %.3f\n", i+1, cost, nr, solve_time);
	    }
	    
	    if (vrp->par.verbosity >4){
	       if(!vrp->dg_id && win){
		  /*vrp->window = init_win(vrp->par.executables.winprog,
		    vrp->par.debug.winprog,
		    vrp->posx, vrp->posy, vrp->vertnum);*/
	       }
	       /*vrp->window->windata.draw = TRUE;
		 disp_lb(vrp->window, temp_tree, temp_best_edges,
		 numroutes, TRUE);*/
	       /*display the lb in the tour window*/
	    }
	 }
	 time(&prev_time); /*reset the time_out timer*/
      }
      else{
#if 0
	 sleep(.01);/* the purpose of this sleep command is to keep the    *\
		    | program from checking the buffer continuously, which  |
		    | chews up CPU time. Before continuing, there is a      |
		    | check to see if too much time has elapsed since the   |
		    | last tour was received and if so all remaining        |
	            \*processes are killed and the function terminates     */
#endif

	 time (&cur_time);
	 if (cur_time > prev_time + vrp->par.time_out.ub){ 
	   if (vrp->par.verbosity>1)
	     printf("\nReceive tours timed out after %i seconds ...\n",
		    vrp->par.time_out.ub);
	   break;
	 }
      }
      for(i=0; i<jobs; i++){
	if(returned[i] != sent[i] && pstat(hh->tids[i]) == PROCESS_OK){
	  receive = 1;
	  break;//break out of loop
	}     
      }
   }
   for (i=0; i<jobs; i++, some_returned+=returned[i]);
   if ((some_returned) && (vrp->par.verbosity >0))
      printf("The best lower bound: %.1f with %u trucks\n",
	     vrp->lb->lower_bound, nr);
   
   if (temp_tree) free ((char *) temp_tree);
   if (hh->starter) free((char *) hh->starter);
   hh->starter = NULL;
   if (returned) free((char *)returned);   
   freebuf(r_bufid);   
   for(i=0; i<jobs; sent[i]=0, i++);
   return (total_solve_time);
}

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
#include <math.h>
#include <stdlib.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_proccomm.h"

/* VRP include files */
#include "vrp_dg.h"
#include "vrp_const.h"
#include "vrp_macros.h"
#include "vrp_messages.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions for the drawgraph process.
\*===========================================================================*/

int user_dg_process_message(void *user, window *win, FILE *write_to)
{
   vrp_dg *win_vrp = (vrp_dg *)user;
   int msgtag;
   int length;
   int *xind;
   double *xval;

   receive_int_array(&msgtag, 1);
   switch (msgtag){
    case VRP_CTOI_DRAW_FRAC_GRAPH:
      receive_int_array(&length, 1);
      xind = (int *) malloc(length * ISIZE);
      xval = (double *) malloc(length * DSIZE);
      receive_int_array(xind, length);
      receive_dbl_array(xval, length);
      dg_freenet(win_vrp->n);
      win_vrp->n = dg_createnet(win->g.nodenum, length, xind, xval);
      FREE(xind);
      FREE(xval);
      dg_net_shrink_chains(win_vrp->n);
      copy_network_into_graph(win_vrp->n, &win->g);
      display_graph_on_canvas(win, write_to);
      break;
   }
   return(USER_NO_PP);
}

/*===========================================================================*/

int user_dg_init_window(void **user, window *win)
{
   vrp_dg *win_vrp = (vrp_dg *) calloc(1, sizeof(vrp_dg));
#if 0
   int vertnum = win_vrp->g.nodenum;

   win_vrp->edges = (int *) calloc (vertnum*(vertnum-1), sizeof(int));

   /*create the edge list (we assume a complete graph)*/
   for (i = 1, k = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
	 vrp->edges[2*k] = j;
	 vrp->edges[2*k+1] = i;
	 k++;
      }
   }
#endif   

   *user = win_vrp;

   return(USER_NO_PP);
}

/*===========================================================================*/

int user_dg_free_window(void **user, window *win)
{
   vrp_dg *win_vrp = (vrp_dg *)*user;

   dg_freenet(win_vrp->n);
   FREE(*user);

   return(USER_NO_PP);
}

/*===========================================================================*/

int user_initialize_dg(void **user)
{
   return(USER_NO_PP);
}

/*===========================================================================*/

int user_free_dg(void **user)
{
   return(USER_NO_PP);
}

/*===========================================================================*/

int user_interpret_text(void *user, int text_length, char *text,
			 int owner_tid)
{
   return(USER_NO_PP);
}


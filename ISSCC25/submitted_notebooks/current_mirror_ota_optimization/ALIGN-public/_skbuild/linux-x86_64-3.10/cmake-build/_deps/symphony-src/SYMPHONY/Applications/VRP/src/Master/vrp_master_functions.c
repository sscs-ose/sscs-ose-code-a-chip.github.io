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
#ifndef WIN32
#include <unistd.h>
#endif
#include <stdio.h>
#include <stdlib.h>
#include <stddef.h>
#include <string.h>
#include <sys/types.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_proccomm.h"

/* VRP include files */
#include "vrp_const.h"
#include "vrp_master_functions.h"
#include "vrp_macros.h"

/*===========================================================================*/

int is_same_edge(const void *ed0, const void *ed1)
{
   return((INDEX(((edge_data *)ed0)->v0, ((edge_data *)ed0)->v1)) -
	  (INDEX(((edge_data *)ed1)->v0, ((edge_data *)ed1)->v1)));
}

/*===========================================================================*/

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
/* This comparison function can be used to sort lexicographically */
/*===========================================================================*/

int is_same_edge(const void *ed0, const void *ed1)
{
   return(((edge_data *)ed0)->v0 - ((edge_data *)ed1)->v0 ?
	  ((edge_data *)ed0)->v0 - ((edge_data *)ed1)->v0 :
	  ((edge_data *)ed0)->v1 - ((edge_data *)ed1)->v1);
}

/*===========================================================================*/
#endif
/*___END_EXPERIMENTAL_SECTION___*/
void delete_dup_edges(small_graph *g)
{
   edge_data *ed0, *ed1;
   int pos;
   int alloc_old = g->allocated_edgenum;   
   
   qsort((char *)g->edges, g->edgenum, sizeof(edge_data), is_same_edge);
   for (pos=0, ed0=ed1=g->edges ; pos < g->edgenum; pos++, ed1++){
      if ( memcmp((char *)ed0, (char *)ed1, 2*sizeof(int)) ){
	 ed0++;
	 if (ed0 != ed1){
	    (void)memcpy((char *)ed0, (char *)ed1, sizeof(edge_data));
	 }
      }
   }
   pos = ((ptrdiff_t)ed0 - (ptrdiff_t)g->edges)/sizeof(edge_data) + 1;
   g->allocated_edgenum -= g->edgenum - pos;
   if (alloc_old){
      g->edges = (edge_data *) realloc
		  ((char *)(g->edges), g->allocated_edgenum * sizeof(edge_data));
   }else {
	  g->edges = (edge_data *) calloc(g->allocated_edgenum, sizeof(edge_data));
   }
   g->edgenum = pos;
}

/*__BEGIN_EXPERIMENTAL_SECTION__*/
/*===========================================================================*/

/*===========================================================================*\
 * This function broadcasts various data that the processes need to
 * compute heuristic solutions.
\*===========================================================================*/

void broadcast(vrp_problem *vrp, int *tids, int jobs)
{
   int s_bufid;

   if (jobs == 0) return;
   
   s_bufid = init_send(DataInPlace);
   send_int_array(&vrp->dist.wtype, 1);
   send_int_array(&vrp->vertnum, 1);
   send_int_array(&vrp->depot, 1);
   send_int_array(&vrp->capacity, 1);
   send_int_array(vrp->demand, (int)vrp->vertnum);
   if (vrp->dist.wtype != _EXPLICIT){ /* not EXPLICIT */
      send_dbl_array(vrp->dist.coordx, vrp->vertnum);
      send_dbl_array(vrp->dist.coordy, vrp->vertnum);
      if ((vrp->dist.wtype == _EUC_3D) || (vrp->dist.wtype == _MAX_3D) || 
	  (vrp->dist.wtype == _MAN_3D))
	 send_dbl_array(vrp->dist.coordz, vrp->vertnum);
   }
   else{ /* EXPLICIT */	
      send_int_array(vrp->dist.cost, (int)vrp->edgenum);
   }
   msend_msg(tids, jobs, VRP_BROADCAST_DATA);
   
   freebuf(s_bufid);
}

/*___END_EXPERIMENTAL_SECTION___*/
/*===========================================================================*/

int *create_edge_list(vrp_problem *vrp, int *varnum, char which_edges)
{
   int i, j, k;
   int zero_varnum, edgenum, new_ind;
   int *zero_vars, *uind = NULL;
   int total_edgenum = vrp->vertnum*(vrp->vertnum-1)/2;

   switch(which_edges){
    case CHEAP_EDGES:

      vrp->zero_vars = zero_vars = (int *) calloc(total_edgenum, sizeof(int));
      
      /*first determine which variables can be fixed to zero permanently*/
      for (zero_varnum=0, i=2; i<vrp->vertnum; i++){
	 for (j=1; j<i; j++){
	    if (vrp->demand[i] + vrp->demand[j] > vrp->capacity){
	       zero_vars[zero_varnum++] = INDEX(i,j);
	    }
	 }
      }
      edgenum = vrp->par.add_all_edges ?
	 vrp->vertnum*(vrp->vertnum-1)/2 : vrp->g->edgenum;
      
      /*First, we construct the index lists*/
      uind = (int *) malloc(edgenum * ISIZE);
      *varnum = 0;
      switch(vrp->par.add_all_edges){
       case FALSE:
	 for (i = 0, j = 0; i<edgenum && j<zero_varnum; i++){
	    new_ind = INDEX(vrp->g->edges[i].v0, vrp->g->edges[i].v1);
	    if (new_ind < zero_vars[j]){
	       uind[(*varnum)++] = new_ind;
	    }else{
	       while (j < zero_varnum && new_ind > zero_vars[j])
		  j++;
	       if (j == zero_varnum){
		  uind[(*varnum)++] = new_ind;	
	       }else if (new_ind < zero_vars[j]){
		  uind[(*varnum)++] = new_ind;
	       }else{
		  j++;
	       }
	    }
	 }
	 /*Now we have exhausted all the zero edges*/
	 for (; i<edgenum; i++)
	    uind[(*varnum)++] =
	       INDEX(vrp->g->edges[i].v0, vrp->g->edges[i].v1);
	 break;
       case TRUE:
	 for (i = 0, j = 0; j<zero_varnum; i++){
	    if (zero_vars[j] == i){
	       j++;
	       continue;
	    }
	    uind[(*varnum)++] = i;
	 }/*Now, we have exhausted all the zero edges*/
	 for (; i <edgenum; i++){
	    uind[(*varnum)++] = i;
	 }
	 break;
      }

#if 0      
      if (vrp->par.verbosity > 0)
	 printf("Fixed %i edges in root creation\n\n", zero_varnum);
#endif
      
      vrp->zero_varnum = zero_varnum;

      break;
      
    case REMAINING_EDGES:

      /*In this case, we are adding all variables at the root, but the small
	graph edges are base and the rest are extra*/

      zero_varnum = vrp->zero_varnum;
      zero_vars = vrp->zero_vars;
      edgenum = vrp->g->edgenum;
      
      uind = (int *) malloc((total_edgenum-edgenum+vrp->vertnum-1) * ISIZE);
      
      *varnum = 0;
      for (i = 0, j = 0, k = 0; i<edgenum; i++, k++){
	 /*In this loop, we check each edge to see if it is in the small
	   graph and whether it is a zero edge*/
	 new_ind = INDEX(vrp->g->edges[i].v0, vrp->g->edges[i].v1);
	 for (; k < new_ind; k++){
	    if ((j < zero_varnum && k < zero_vars[j]) || j >= zero_varnum){
	       uind[(*varnum)++] = k;
	    }else{
	       while (j < zero_varnum && k > zero_vars[j])
		  j++;
	       if (j == zero_varnum){
		  uind[(*varnum)++] = k;	
	       }else if (k < zero_vars[j]){
		  uind[(*varnum)++] = k;
	       }else{
		  j++;
	       }
	    }
	 }
	 /*k == new_ind here so we don't want to add that edge */
      }
      /*Now, we have exhausted the small graph so just add all non-zero
	edges*/
      while (j < zero_varnum && k > zero_vars[j])
	 j++;
      for (; k<total_edgenum && j<zero_varnum; k++)
	 if (k < zero_vars[j])
	    uind[(*varnum)++] = k;
	 else
	    j++;
      /* Now, there are no more non-zero edges either so add the rest*/
      for (; k<total_edgenum; k++)
	 uind[(*varnum)++] = k;

      break;
   }
   
   return(uind);
}

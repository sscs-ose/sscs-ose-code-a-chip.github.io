/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* Capacitated Network Routing Problems.                                     */
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
#include "sym_qsort.h"

/* CNRP include files */
#include "cnrp_const.h"
#include "cnrp_master_functions.h"
#include "cnrp_macros.h"

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
/*__END_EXPERIMENTAL_SECTION__*/
void delete_dup_edges(small_graph *g)
{
   edge_data *ed0, *ed1;
   int pos;
   
   qsort((char *)g->edges, g->edgenum, sizeof(edge_data), 
	 is_same_edge);
   for (pos=0, ed0=ed1=g->edges ; pos < g->edgenum; pos++, ed1++){
      if ( memcmp((char *)ed0, (char *)ed1, 2*sizeof(int)) ){
	 ed0++;
	 (void)memcpy((char *)ed0, (char *)ed1, sizeof(edge_data));
      }
   }
   pos = ed0 - g->edges + 1;
   g->allocated_edgenum -= g->edgenum - pos;
   g->edges = (edge_data *) realloc
      ((char *)(g->edges), g->allocated_edgenum * sizeof(edge_data));
   g->edgenum = pos;
}

/*===========================================================================*\
 * This is the function that creates the list of variables (edges in the graph)
\*===========================================================================*/

void cnrp_create_variables(cnrp_problem *cnrp)
{
   int base_varnum = 0, i, j, k, l;
   int zero_varnum, *zero_vars;
   int *edges;
   int vertnum = cnrp->vertnum;
   
#ifdef DIRECTED_X_VARS
   /*whether or not we will have the out-degree constraints*/
   char od_const = (cnrp->par.prob_type == TSP || cnrp->par.prob_type == VRP ||
		    cnrp->par.prob_type == BPP);
   char d_x_vars = TRUE;
#else
   char od_const = FALSE;
   char d_x_vars = FALSE;
#endif
   int total_edgenum = vertnum*(vertnum - 1)/2;
#ifdef ADD_FLOW_VARS
   int v0, v1;
   double flow_capacity;
#ifdef DIRECTED_X_VARS
   flow_capacity = cnrp->capacity;
#else
   if (cnrp->par.prob_type == CSTP || cnrp->par.prob_type == CTP)
      flow_capacity = cnrp->capacity;
   else
      flow_capacity = cnrp->capacity/2;
#endif
#endif
   
#ifdef ADD_CAP_CUTS 
   cnrp->basecutnum = (2 + od_const)*vertnum - 1 + 2*total_edgenum;
#elif defined(ADD_FLOW_VARS)
   cnrp->basecutnum = (2 + od_const)*vertnum - 1;
#else
   cnrp->basecutnum = (1 + od_const)*vertnum;
#endif
#ifdef ADD_X_CUTS
   cnrp->basecutnum += total_edgenum;
#endif
#if defined(FIND_NONDOMINATED_SOLUTIONS) && 0
   cnrp->basecutnum += 2; /* Need two extra constraints */
#endif
   
   switch(cnrp->par.base_variable_selection){
    case SOME_ARE_BASE:
      if (cnrp->par.add_all_edges == FALSE){
	 /*If we are not adding all the edges, then really EVERYTHING_IS_BASE*/
	 cnrp->par.base_variable_selection = EVERYTHING_IS_BASE;
      }else{ /*Otherwise, all we need to do is set this and then fall
	       through -- the remaining edges get added later */
	 cnrp->par.add_all_edges = FALSE;
      }

    case EVERYTHING_IS_BASE:
      cnrp->basevars = create_edge_list(cnrp, &base_varnum, CHEAP_EDGES);
#ifdef FIND_NONDOMINATED_SOLUTIONS
      cnrp->basevars = (int *) realloc((char *)cnrp->basevars,
				       (base_varnum + 1) * ISIZE);
      cnrp->basevarnum = base_varnum + 1; /* Need one extra variable */
#ifdef ADD_FLOW_VARS
      cnrp->basevars[base_varnum] = d_x_vars ? 4*total_edgenum:3*total_edgenum;
#else
      cnrp->basevars[base_varnum] = d_x_vars ? total_edgenum:2*total_edgenum;
#endif	 
#else
      cnrp->basevars = (int *) realloc((char *)cnrp->basevars,
				       base_varnum * ISIZE);
      cnrp->basevarnum = base_varnum;
#endif
      break;

    case EVERYTHING_IS_EXTRA:
      cnrp->basevarnum = 0;
      break;
   }

#if 0
   if (cnrp->par.prob_tpye == BPP){
      for (i = 0; i < cnrp->basevarnum; i++){
	 cnrp->dist.cost[cnrp->basevars[i]] = 10;
      }
   }
#endif
       
   /* The one additional edge allocated is for the extra variable when finding
      nondominated solutions for multi-criteria problems */  
   edges = cnrp->edges = (int *) calloc (vertnum*(vertnum-1) + 2, sizeof(int));

   /* Create the edge list (we assume a complete graph) The edge is set to
      (0,0) in the edge list if it was eliminated in preprocessing*/
   /* For now, we cannot preprocess anything out because SYMPHONY assumes all
      variables are present */
   zero_varnum = cnrp->zero_varnum;
   zero_vars = cnrp->zero_vars;
   for (i = 1, k = 0, l = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
#if 0
	 if (l < zero_varnum && k == zero_vars[l]){
	    /*This is one of the zero edges*/
	    edges[2*k] = edges[2*k+1] = 0;
	    l++;
	    k++;
	    continue;
	 }
#endif
	 edges[2*k] = j;
	 edges[2*k+1] = i;
	 k++;
      }
   }
   edges[vertnum*(vertnum-1)] = edges[vertnum*(vertnum-1) + 1] = 0;
   
   switch(cnrp->par.base_variable_selection){
    case EVERYTHING_IS_EXTRA:

      cnrp->extravars  = create_edge_list(cnrp, &cnrp->extravarnum,
					  CHEAP_EDGES);
#if defined(FIND_NONDOMINATED_SOLUTIONS) && 0
      cnrp->extravars = cnrp->extravars + 1;
#endif

      break;

    case SOME_ARE_BASE:
      
      cnrp->par.add_all_edges = TRUE; /*We turned this off in user_set_base()
				       -- now we need to turn it back on*/

      cnrp->extravars  = create_edge_list(cnrp, &cnrp->extravarnum,
					  REMAINING_EDGES);

      break;

    case EVERYTHING_IS_BASE:

      break;
   }
}   

/*===========================================================================*/

int *create_edge_list(cnrp_problem *cnrp, int *varnum, char which_edges)
{
   int i, j, k;
   int zero_varnum, edgenum, new_ind;
   int *zero_vars, *uind = NULL;
   int total_edgenum = cnrp->vertnum*(cnrp->vertnum-1)/2;
#ifdef DIRECTED_X_VARS
   char d_x_vars = TRUE;
#else
   char d_x_vars = FALSE;
#endif

   /*DIFF: This routine has to be modified to include the flow variables*/

   switch(which_edges){
    case CHEAP_EDGES:

      cnrp->zero_vars = zero_vars = (int *) calloc(total_edgenum, sizeof(int));
      
      /*first determine which variables can be fixed to zero permanently*/
      for (zero_varnum=0, i=2; i<cnrp->vertnum; i++){
	 for (j=1; j<i; j++){
	    if (cnrp->demand[i] + cnrp->demand[j] > cnrp->capacity){
	       zero_vars[zero_varnum++] = INDEX(i,j);
	    }
	 }
      }
      
      edgenum = cnrp->par.add_all_edges ?
	 cnrp->vertnum*(cnrp->vertnum-1)/2 : cnrp->g->edgenum;
      
      /*First, we construct the index lists*/
#ifdef ADD_FLOW_VARS
      uind = (int *) malloc((3+d_x_vars) * edgenum * ISIZE);
#else
      uind = (int *) malloc((1+d_x_vars) * edgenum * ISIZE);
#endif
      
      *varnum = 0;
      switch(cnrp->par.add_all_edges){
       case FALSE:
	 for (i = 0, j = 0; i<edgenum && j<zero_varnum; i++){
	    new_ind = INDEX(cnrp->g->edges[i].v0, cnrp->g->edges[i].v1);
	    if (new_ind < zero_vars[j]){
	       uind[(*varnum)++] = new_ind;                 /*edge var*/
#ifdef DIRECTED_X_VARS
	       uind[(*varnum)++] = total_edgenum + new_ind; /*edge var*/
#endif
#ifdef ADD_FLOW_VARS
	       /*flow var*/
	       uind[(*varnum)++] = (1+d_x_vars)*total_edgenum + new_ind;
	       /*flow var*/
	       uind[(*varnum)++] = (2+d_x_vars)*total_edgenum + new_ind;
#endif
	    }else{
	       while (j < zero_varnum && new_ind > zero_vars[j])
		  j++;
	       if (j == zero_varnum){
		  uind[(*varnum)++] = new_ind;                   /*edge var*/
#ifdef DIRECTED_X_VARS
		  uind[(*varnum)++] = total_edgenum + new_ind;   /*edge var*/
#endif
#ifdef ADD_FLOW_VARS
		  /*flow var*/
		  uind[(*varnum)++] = (1+d_x_vars)*total_edgenum + new_ind;
		  /*flow var*/
		  uind[(*varnum)++] = (2+d_x_vars)*total_edgenum + new_ind;
#endif
	       }else if (new_ind < zero_vars[j]){
		  uind[(*varnum)++] = new_ind;                   /*edge var*/
#ifdef DIRECTED_X_VARS
		  uind[(*varnum)++] = total_edgenum + new_ind;   /*edge var*/
#endif
#ifdef ADD_FLOW_VARS
		  /*flow var*/
		  uind[(*varnum)++] = (1+d_x_vars)*total_edgenum + new_ind;
		  /*flow var*/
		  uind[(*varnum)++] = (2+d_x_vars)*total_edgenum + new_ind;
#endif
	       }else
		  j++;
	    }
	 }
	 /*Now we have exhausted all the zero edges*/
	 for (; i<edgenum; i++){
	    uind[(*varnum)++] =
	       INDEX(cnrp->g->edges[i].v0, cnrp->g->edges[i].v1);
#ifdef DIRECTED_X_VARS
	    uind[(*varnum)++] =
	       total_edgenum +
	       INDEX(cnrp->g->edges[i].v0, cnrp->g->edges[i].v1);
#endif
#ifdef ADD_FLOW_VARS
	    uind[(*varnum)++] =
	       (1+d_x_vars)*total_edgenum+INDEX(cnrp->g->edges[i].v0,
						cnrp->g->edges[i].v1);
	    uind[(*varnum)++] =
	       (2+d_x_vars)*total_edgenum+INDEX(cnrp->g->edges[i].v0,
						cnrp->g->edges[i].v1);
#endif
	 }
	 break;
       case TRUE:
	 for (i = 0, j = 0; j<zero_varnum; i++){
	    if (zero_vars[j] == i){
	       j++;
	       continue;
	    }
	    uind[(*varnum)++] = i;                    /*edge variable*/
#ifdef DIRECTED_X_VARS
	    uind[(*varnum)++] = total_edgenum + i;    /*edge variable*/
#endif
#ifdef ADD_FLOW_VARS
	    /*flow var*/
	    uind[(*varnum)++] = (1+d_x_vars)*total_edgenum + i;
	    /*flow var*/
	    uind[(*varnum)++] = (2+d_x_vars)*total_edgenum + i;
#endif
	 }/*Now, we have exhausted all the zero edges*/
	 for (; i < edgenum; i++){
	    uind[(*varnum)++] = i;                    /*edge variable*/
#ifdef DIRECTED_X_VARS
	    uind[(*varnum)++] = total_edgenum + i;    /*edge variable*/
#endif
#ifdef ADD_FLOW_VARS
	    /*flow var*/
	    uind[(*varnum)++] = (1+d_x_vars)*total_edgenum + i;
	    /*flow var*/
	    uind[(*varnum)++] = (2+d_x_vars)*total_edgenum + i;
#endif
	 }
	 break;
      }

      if (cnrp->par.verbosity > 0)
	 printf("Fixed %i edges in root creation\n\n", zero_varnum);
      
      cnrp->zero_varnum = zero_varnum;

      break;
      
    case REMAINING_EDGES:

      /*In this case, we are adding all variables at the root, but the small
	graph edges are base and the rest are extra*/

      zero_varnum = cnrp->zero_varnum;
      zero_vars = cnrp->zero_vars;
      edgenum = cnrp->g->edgenum;

#ifdef ADD_FLOW_VARS
      uind = (int *) malloc((3 + d_x_vars) *
			    (total_edgenum-edgenum+cnrp->vertnum -1)* ISIZE);
#else
      uind = (int *) malloc((1 + d_x_vars) *
			    (total_edgenum-edgenum+cnrp->vertnum-1) * ISIZE);
#endif
      *varnum = 0;
      for (i = 0, j = 0, k = 0; i < edgenum; i++, k++){
	 /*In this loop, we check each edge to se if it is in the small
	   graph and whether it is a zero edge*/
	 new_ind = INDEX(cnrp->g->edges[i].v0, cnrp->g->edges[i].v1);
	 for (; k < new_ind; k++){
	    if ((j < zero_varnum && k < zero_vars[j]) || j >= zero_varnum){
	       uind[(*varnum)++] = k;                    /*edge variable*/
#ifdef DIRECTED_X_VARS
	    uind[(*varnum)++] = total_edgenum + k;       /*edge variable*/
#endif
#ifdef ADD_FLOW_VARS
	    /*flow var*/
	    uind[(*varnum)++] = (1+d_x_vars)*total_edgenum + k;
	    /*flow var*/
	    uind[(*varnum)++] = (2+d_x_vars)*total_edgenum + k;
#endif
	    }else{ /*curent edge is a zero edge so don't add it*/
	       j++;
	    }
	 }
	 /*k == new_ind here so we don't want to add that edge */
      }
      /*Now, we have exhausted the small graph so just add all non-zero
	edges*/
      for (; k < total_edgenum && j < zero_varnum; k++)
	 if (k < zero_vars[j]){
	    uind[(*varnum)++] = k;                    /*edge variable*/
#ifdef DIRECTED_X_VARS
	    uind[(*varnum)++] = total_edgenum + k;    /*edge variable*/
#endif
#ifdef ADD_FLOW_VARS
	    /*flow var*/
	    uind[(*varnum)++] = (1+d_x_vars)*total_edgenum + k;
	    /*flow var*/
	    uind[(*varnum)++] = (2+d_x_vars)*total_edgenum + k;
#endif
	 }else{
	    j++;
	 }
      /* Now, there are no more non-zero edges either so add the rest*/
      for (; k < total_edgenum; k++){
	 uind[(*varnum)++] = k;                    /*edge variable*/
#ifdef DIRECTED_X_VARS
	 uind[(*varnum)++] = total_edgenum + k;    /*edge variable*/
#endif
#ifdef ADD_FLOW_VARS
	 /*flow var*/
	 uind[(*varnum)++] = (1+d_x_vars)*total_edgenum + k;
	 /*flow var*/
	 uind[(*varnum)++] = (2+d_x_vars)*total_edgenum + k;
#endif
      }
      break;
   }
   qsort_i(uind, *varnum);

   return(uind);
}

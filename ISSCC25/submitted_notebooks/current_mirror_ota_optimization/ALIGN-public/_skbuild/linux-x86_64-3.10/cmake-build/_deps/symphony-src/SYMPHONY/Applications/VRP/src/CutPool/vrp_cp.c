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
#include <string.h>
#include <stdlib.h>
#include <stdio.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_types.h"
#include "sym_proccomm.h"
#include "sym_cp_u.h"

/* VRP include files */
#include "vrp_cp.h"
#include "vrp_const.h"
#include "vrp_macros.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions of the cut pool process.
\*===========================================================================*/

/*===========================================================================*\
 * Here is where the user must receive all of the data sent from
 * user_send_cp_data() and set up data structures. Note that this function is
 * only called if one of COMPILE_IN_CP, COMPILE_IN_LP, or COMPILE_IN_TM is
 * FALSE.
\*===========================================================================*/

int user_receive_cp_data(void **user)
{
   vrp_cp_problem *vcp = (vrp_cp_problem *) calloc (1, sizeof(vrp_cp_problem));  
   int i, j, k;

   *user = (void *) vcp;

   receive_int_array(&vcp->vertnum, 1);
   
   vcp->edgenum = vcp->vertnum*(vcp->vertnum-1)/2 + vcp->vertnum-1;
   vcp->edges = (int *) calloc ((int)2*vcp->edgenum, sizeof(int));
     
   /* create the edge list (we assume a complete graph) */
   for (i = 1, k = 0; i < vcp->vertnum; i++){
      for (j = 0; j < i; j++){
	 vcp->edges[2*k] = j;
	 vcp->edges[2*k+1] = i;
	 k++;
      }
   }

   /* now add the duplicate copies of the depot edges to allow for
      routes with one customer */
   for (i = 1; i < vcp->vertnum; i++){
      vcp->edges[2*k] = 0;
      vcp->edges[2*k+1] = i;
      k++;
   }
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we free up the data structures
\*===========================================================================*/

int user_free_cp(void **user)
{
   vrp_cp_problem *vcp = (vrp_cp_problem *)(*user);

   FREE(vcp->edges);
   FREE(vcp);
   *user = NULL;

   return(USER_SUCCESS);
}

/*===========================================================================*/

int user_receive_lp_solution_cp(void *user)
{
   /* We leave this to SYMPHONY */
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * When a new solution arrives to the cut pool, this function is invoked
 * so that the user can prepare for checking many cuts (probably set up
 * some data structures that make ckecking more efficient). In our
 * case, we construct a fractional graph representation of the LP
 * solution, which will be more efficient for checking the cuts.
\*===========================================================================*/

int user_prepare_to_check_cuts(void *user, int varnum, int *indices,
				double *values)
{
   vrp_cp_problem *vcp = (vrp_cp_problem *)user;
   vcp->n = create_pool_net(vcp, varnum, indices, values);

   return(USER_SUCCESS);
}


/*===========================================================================*/

/*===========================================================================*\
 * Check to see whether a particular cut is violated by the current LP sol.
\*===========================================================================*/
      
int user_check_cut(void *user, double etol, int varnum, int *indices,
		   double *values, cut_data *cut, int *is_violated,
		   double *quality)
{
   vrp_cp_problem *vcp = (vrp_cp_problem *)user;
   pool_net *n;
   char *coef;
   int v0, v1;
   pool_node *verts;
   int vertnum;
   double lhs = 0;
   pool_edge *cur_edge;
   int i;
   int j, cliquecount, size;
   char *clique_array;
   /*__BEGIN_EXPERIMENTAL_SECTION__*/

   int  num_arcs = 0, edge_index; 
   char *cpt; 
   int *arcs ;
   char *indicators;
   double bigM, *weights ;
   int jj, num_fracs = 0, fracs = 0;
   /*___END_EXPERIMENTAL_SECTION___*/

   n = vcp->n;
   verts = n->verts;
   vertnum = n->vertnum;
   
   /*------------------------------------------------------------------------*\
    * Here the cut is "unpacked" and checked for violation. Each cut is
    * stored as compactly as possible. The subtour elimination constraints
    * are stored as a vector of bits indicating which side of the cut each
    * node is on. If the cut is violated, it is sent back to the lp.
    * Otherwise, "touches" is incremented. "Touches" is a measure of the
    * effectiveness of a cut and indicates how long it has been since a
    * cut was useful
   \*------------------------------------------------------------------------*/
   switch (cut->type){
    
    case SUBTOUR_ELIM_SIDE:
      coef = cut->coef;
      for (lhs = 0, v0 = 0; v0 < vertnum; v0++){
	 if (!(coef[v0 >> DELETE_POWER] & (1 << (v0 & DELETE_AND))))
	    continue;
	 for(cur_edge = verts[v0].first; cur_edge; cur_edge = cur_edge->next){
	    v1 = cur_edge->other_end;
	    if (coef[v1 >> DELETE_POWER] & (1 << (v1 & DELETE_AND)))
	       lhs += cur_edge->weight;
	 }
      }
      *is_violated = (lhs/2 > (double)(cut->rhs)+etol);
      *quality   = lhs/2 - (double)cut->rhs;
      if (*quality < etol && *quality > -etol) *quality = 0;
      return(USER_SUCCESS);

    case SUBTOUR_ELIM_ACROSS:
      coef = cut->coef;
      for (lhs = 0, i = 0; i<varnum; i++){
	 v0 = vcp->edges[indices[i] << 1];
	 v1 = vcp->edges[(indices[i] << 1) + 1];
	 if ((coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1) ^
	     (coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1))
	    lhs += values[i];
      }
      *is_violated = (lhs < (double)(cut->rhs)-etol);
      *quality   = (double)cut->rhs - lhs;
      if (*quality < etol && *quality > -etol) *quality = 0;
      return(USER_SUCCESS);

    case CLIQUE:
      coef = cut->coef;
      size = (vertnum >> DELETE_POWER) + 1;
      memcpy(&cliquecount, coef, ISIZE);
      coef += ISIZE;
      for (lhs = 0, v0 = 0; v0 < vertnum; v0++){
	 for (j = 0; j < cliquecount; j++){
	    clique_array = coef + size * j;
	    if (!(clique_array[v0>>DELETE_POWER] & (1<<(v0 & DELETE_AND))))
	       continue;
	    for (cur_edge = verts[v0].first; cur_edge;
		 cur_edge = cur_edge->next){
	       v1 = cur_edge->other_end;
	       if (coef[v1 >> DELETE_POWER] & (1 << (v1 & DELETE_AND)))
		  lhs += cur_edge->weight;
	    }
	 }
      }
      *is_violated = (lhs < cut->rhs - etol); 
      *quality   = (double)cut->rhs - lhs;
      if (*quality < etol && *quality > -etol) *quality = 0;
      return(USER_SUCCESS);
      
    /*__BEGIN_EXPERIMENTAL_SECTION__*/
    case FARKAS:
      coef = cut->coef;
      cpt = coef+ ((vertnum >> DELETE_POWER) + 1); 
      memcpy((char *)&num_arcs, cpt, ISIZE);
      cpt += ISIZE;
      arcs = (int *) malloc(num_arcs * ISIZE);
      indicators = (char *) malloc(num_arcs);  
      memcpy((char *)arcs, cpt, ISIZE*(num_arcs));
      cpt += num_arcs * ISIZE;
      memcpy(indicators, cpt, num_arcs);
      cpt += num_arcs;
      memcpy((char *)&num_fracs, cpt, ISIZE);
      cpt += ISIZE;
      weights = (double *) malloc((num_fracs + 1) * DSIZE);
      memcpy((char *)weights, cpt, (num_fracs + 1) * DSIZE);
      bigM = (*(double *)weights);
      weights++;
      
      for (fracs = 0, i = 0, lhs = 0 ; i < varnum; i++){
	 v0 = vcp->edges[indices[i] << 1];
	 v1 = vcp->edges[(indices[i] << 1) + 1];
	 /*edge_index=INDEX(v0, v1);*/
	 edge_index = indices[i];
	 if (isset(coef, v1) || isset(coef,v0)){
	    for (jj = 0; jj < num_arcs; jj++){
	       if (arcs[jj] == edge_index){
		  if (indicators[jj]){
		     lhs += -bigM*values[i];
		     break;
		  }else{
		     lhs += weights[fracs++]*values[i];
		     break;
		  }
	       }
	    }
	    if (jj == num_arcs) lhs += bigM*values[i];
	 }
      }
      weights--;
      FREE(arcs);
      FREE(indicators);
      FREE(weights);
      *is_violated = (lhs < cut->rhs - etol); 
      *quality   = (double)cut->rhs - lhs;
      if (*quality < etol && *quality > -etol) *quality = 0;
      return(USER_SUCCESS);
      
    case NO_COLUMNS:
      coef = cut->coef;
      cpt = coef+ ((vertnum >> DELETE_POWER) + 1); 
      memcpy((char *)&num_arcs, cpt, ISIZE);
      arcs = (int *) malloc(num_arcs * ISIZE);
      indicators = (char *) malloc(num_arcs);
      cpt += ISIZE;
      memcpy((char *)arcs, cpt, num_arcs * ISIZE);
      cpt += num_arcs * ISIZE;
      memcpy(indicators, cpt, num_arcs);
      
      for (i = 0, lhs = 0 ; i < varnum; i++){
	 v0 = vcp->edges[indices[i] << 1];
	 v1 = vcp->edges[(indices[i] << 1) + 1];
	 /*edge_index = INDEX(v0, v1);*/
	 edge_index = indices[i];
	 if (isset(coef, v1) || isset(coef,v0)){
	    for (jj = 0; jj < num_arcs; jj++){
	       if ( arcs[jj] == edge_index){
		  lhs += indicators[jj] ? values[i] : 0.0;
		  break;
	       }
	    }
	    if (jj == num_arcs) lhs -= values[i];
	 }
      }
      FREE(arcs);
      FREE(indicators);
      *is_violated = (lhs > cut->rhs + etol); 
      *quality   = lhs - (double)cut->rhs;
      if (*quality < etol && *quality > -etol) *quality = 0;
      return(USER_SUCCESS);
      
    case GENERAL_NONZEROS:
      cpt = cut->coef;
      memcpy((char *)&num_arcs, cpt, ISIZE);
      cpt += ISIZE;
      arcs = (int *) calloc(num_arcs, ISIZE);
      weights = (double *) calloc(num_arcs, DSIZE);
      memcpy((char *)arcs, cpt, num_arcs * ISIZE);
      cpt += num_arcs * ISIZE;
      memcpy((char *)weights, cpt, num_arcs * DSIZE);
      
      for (i = 0, lhs = 0; i < varnum; i++){
	 edge_index = indices[i];
	 for (j = 0; j < num_arcs; j++){
	    if (arcs[j] == edge_index)
	       lhs += values[i]*weights[j];
	 }
      }
      FREE(arcs);
      FREE(weights);
      *is_violated = (cut->sense == 'G' ? (lhs < cut->rhs + etol) :
		                          (lhs > cut->rhs - etol));
      *quality   = (cut->sense == 'G' ? (double)cut->rhs - lhs :
		                           lhs - (double)cut->rhs);
      if (*quality < etol && *quality > -etol) *quality = 0;
      return(USER_SUCCESS);
      
    /*___END_EXPERIMENTAL_SECTION___*/
    default:
      printf("Cut types not recognized! \n\n");
      *is_violated = FALSE;
      return(USER_SUCCESS);
   }
}

/*===========================================================================*/

/*===========================================================================*\
 * This function is invoked when all cuts that needed to be checked for
 * the current solution have been checked already. (Disassemble the
 * data structures built up in 'user_prepare_to_check_cuts'.
\*===========================================================================*/

int user_finished_checking_cuts(void *user)
{
   vrp_cp_problem *vcp = (vrp_cp_problem *)user;
   free_pool_net(vcp);

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function creates the solution graph from the current LP solution
\*===========================================================================*/

pool_net *create_pool_net(vrp_cp_problem *vcp, int varnum, int *indices,
			  double *values)
{
   register int *edges = vcp->edges;
   pool_net *n;
   pool_node *verts;
   int nv0 = 0, nv1 = 0;
   pool_edge *adjlist;
   int i;
   int vertnum = vcp->vertnum;
   int edgenum = vcp->edgenum;
   
   n = (pool_net *) calloc (1, sizeof(pool_net));
   n->vertnum = vertnum;
   n->edgenum = varnum;
   n->verts = (pool_node *)calloc((int)vertnum, sizeof(pool_node));
   n->adjlist = (pool_edge *)calloc(2*(int)edgenum, sizeof(pool_edge));
   verts = n->verts;
   adjlist = n->adjlist;
  
   for (i = 0; i < varnum; i++){
      nv0 = edges[indices[i] << 1];
      nv1 = edges[(indices[i] << 1) + 1];
      if (!verts[nv0].first)
	 verts[nv0].first = adjlist;
      else{
	 adjlist->next = verts[nv0].first;
	 verts[nv0].first = adjlist;
      }
      adjlist->other_end = nv1;
      adjlist->weight = values[i];
      adjlist++;
      if (!verts[nv1].first)
	 verts[nv1].first = adjlist;
      else{
	 adjlist->next = verts[nv1].first;
	 verts[nv1].first = adjlist;
      }
      adjlist->other_end = nv0;
      adjlist->weight = values[i];
      adjlist++;
   }
   
   return(n);
}

/*===========================================================================*/

/*===========================================================================*\
 * Frees the memory associated with a solution network
\*===========================================================================*/

void free_pool_net(vrp_cp_problem *vcp)
{
   if (vcp->n){
      FREE(vcp->n->adjlist);
      FREE(vcp->n->verts);
      FREE(vcp->n);
   }
}

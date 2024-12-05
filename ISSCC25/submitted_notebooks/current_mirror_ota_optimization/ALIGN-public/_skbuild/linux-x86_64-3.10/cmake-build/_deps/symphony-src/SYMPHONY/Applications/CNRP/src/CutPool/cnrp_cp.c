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
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_types.h"
#include "sym_proccomm.h"
#include "sym_cp_u.h"

/* CNRP include files */
#include "cnrp_cp.h"
#include "cnrp_const.h"
#include "cnrp_macros.h"

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
   cnrp_spec_cp *vcp = (cnrp_spec_cp *) calloc (1, sizeof(cnrp_spec_cp));  
   int i, j, k;

   *user = (void *) vcp;

   receive_int_array(&vcp->vertnum, 1);
   receive_dbl_array(&vcp->capacity, 1);
   vcp->demand = (double *) malloc(vcp->vertnum * DSIZE);
   receive_dbl_array(vcp->demand, vcp->vertnum);
   
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
   cnrp_spec_cp *vcp = (cnrp_spec_cp *)(*user);

   FREE(vcp->edges);
   FREE(vcp->demand);
   FREE(vcp);
   *user = NULL;

   return(USER_SUCCESS);
}

/*===========================================================================*/

int user_receive_lp_solution_cp(void *user)
{
   /* We leave this to SYMPHONY */
   return(USER_SUCCESS);
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
   cnrp_spec_cp *vcp = (cnrp_spec_cp *)user;

#if 0
#ifdef ADD_FLOW_VARS
   int total_edgenum = vcp->vertnum*(vcp->vertnum - 1)/2;
   int i;
#endif
   
#ifdef ADD_FLOW_VARS
#ifdef DIRECTED_X_VARS
   for (i = 0; indices[i] < 2*total_edgenum; i++);
#else
   for (i = 0; indices[i] < total_edgenum; i++);
#endif
   varnum = i;
#endif
   
   vcp->n = create_pool_net(vcp, varnum, indices, values);
#endif

   vcp->n = NULL;
   
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
   cnrp_spec_cp *vcp = (cnrp_spec_cp *)user;
   char *coef, *coef2;
   int index, v0, v1;
   int vertnum = vcp->vertnum;
   double lhs = 0;
   int i, j, k, cliquecount, size;
   char *clique_array;
#if defined(ADD_FLOW_VARS) || defined(DIRECTED_X_VARS)
   int total_edgenum = vcp->vertnum*(vcp->vertnum - 1)/2;
#endif
   int *edges = vcp->edges, *matind, *arcs;
   int edgeind, numarcs;
   double demand, capacity = vcp->capacity;
   char first_coeff_found, second_coeff_found, third_coeff_found, d_x_vars;

      coef = cut->coef;
      
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

    case SUBTOUR_ELIM:
    case SUBTOUR_ELIM_SIDE:
       for (i = 0; i < varnum; i++){
#ifdef ADD_FLOW_VARS
#ifdef DIRECTED_X_VARS
	  if (indices[i] < 2*total_edgenum){
	      if (indices[i] >= total_edgenum){
		 edgeind = indices[i] - total_edgenum;
	      }else{
		 edgeind = indices[i];
	      }
#else
	   if ((edgeind = indices[i]) < total_edgenum){   
#endif
#else
#ifdef DIRECTED_X_VARS
	   {
	      if (indices[i] >= total_edgenum){
		 edgeind = indices[i] - total_edgenum;
	      }else{
		 edgeind = indices[i];
	      }
#else	      
           {
	      edgeind = indices[i];
#endif
#endif
	      v0 = edges[edgeind << 1];
	      v1 = edges[(edgeind << 1) + 1];
	      if (coef[v0 >> DELETE_POWER] & (1 << (v0 & DELETE_AND)) &&
		  (coef[v1 >> DELETE_POWER]) & (1 << (v1 & DELETE_AND))){
		 lhs += values[i];
	      }
	   }
	}
	*is_violated = (lhs > (double)(cut->rhs)+etol);
        *quality   = lhs - (double)cut->rhs;
        if (*quality < etol && *quality > -etol) *quality = 0;
        return(USER_SUCCESS);

    case SUBTOUR_ELIM_ACROSS:
      for (i = 0; i < varnum; i++){
#ifdef DIRECTED_X_VARS
#ifdef ADD_FLOW_VARS
	   if (indices[i] < 2*total_edgenum){
#else
	   {
#endif
	      if (indices[i] >= total_edgenum){
		 edgeind = indices[i] - total_edgenum;
		 v1 = edges[edgeind << 1];
		 v0 = edges[(edgeind << 1) + 1];
	      }else{
		 edgeind = indices[i];
		 v0 = edges[edgeind << 1];
		 v1 = edges[(edgeind << 1) + 1];
	      }
	      if ((coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1) &&
		  !(coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1)){
		 lhs += values[i];
	      }
	   }
#else
#ifdef ADD_FLOW_VARS
	   if (indices[i] < total_edgenum){   
#else	      
           {
#endif
	      edgeind = indices[i];
	      v0 = edges[edgeind << 1];
	      v1 = edges[(edgeind << 1) + 1];
	      if ((coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1) ^
		  (coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1)){
		 lhs += values[i];
	      }
	   }
#endif
	}
      *is_violated = (lhs < (double)(cut->rhs)-etol);
      *quality   = (double)cut->rhs - lhs;
      if (*quality < etol && *quality > -etol) *quality = 0;
      return(USER_SUCCESS);

#if defined(ADD_FLOW_VARS) && defined(DIRECTED_X_VARS)
      case MIXED_DICUT:
	demand = ((double *)coef)[0];
	numarcs = ((int *)(coef + DSIZE))[0];
	/* Array of the nodes in the set S */
	coef2 = coef + DSIZE + ISIZE;
	/* Array of the arcs in the set C */
	arcs = (int *) (coef + DSIZE + ISIZE + (vertnum >> DELETE_POWER)+1); 
	for (i = 0; i < varnum; i++){
	   if (indices[i] < 2*total_edgenum){
	      if (indices[i] >= total_edgenum){
		 edgeind = indices[i] - total_edgenum;
		 v1 = edges[edgeind << 1];
		 v0 = edges[(edgeind << 1) + 1];
	      }else{
		 edgeind = indices[i];
		 v0 = edges[edgeind << 1];
		 v1 = edges[(edgeind << 1) + 1];
	      }
	      if ((coef2[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1) &&
		  !(coef2[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1)){
		 for (k = 0; k < numarcs; k++){
		    if (v0 == arcs[k << 1] && v1 == arcs[(k << 1) + 1])
		       break;
		 }
		 if (k == numarcs){
		    lhs += values[i]*MIN(vcp->capacity, demand);
		 }
	      }
	   }else{
	      if (indices[i] < 3*total_edgenum){
		 edgeind = indices[i] - 2*total_edgenum;
		 v0 = edges[edgeind << 1];
		 v1 = edges[(edgeind << 1) + 1];
	      }else{
		 edgeind = indices[i] - 3*total_edgenum;
		 v1 = edges[edgeind << 1];
		 v0 = edges[(edgeind << 1) + 1];
	      }
	      if ((coef2[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1) &&
		  !(coef2[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1)){
		 for (k = 0; k < numarcs; k++){
		    if (v0 == arcs[k << 1] && v1 == arcs[(k << 1) + 1])
		       break;
		 }
		 if (k < numarcs){
		    lhs += values[i];
		 }
	      }
	   }
	}
	*is_violated = (lhs < (double)(cut->rhs)-etol);
	*quality   = (double)cut->rhs - lhs;
	if (*quality < etol && *quality > -etol) *quality = 0;
	return(USER_SUCCESS);
#endif
	
#ifdef ADD_FLOW_VARS
      case FLOW_CAP:
	matind = (int *)    malloc(3 * ISIZE);
	index = ((int *)coef)[0];
	v0 = index < total_edgenum ? edges[index << 1] :
	   edges[(index - total_edgenum) << 1];
	v1 = index < total_edgenum ? edges[(index << 1) + 1] :
	   edges[((index - total_edgenum) << 1) + 1];
	if (v0){
	   demand =
	      index < total_edgenum ? vcp->demand[v0] : vcp->demand[v1];
	}else{
	   demand = 0;
	}
	
	first_coeff_found = second_coeff_found = third_coeff_found = FALSE;
	for (i = 0; i < varnum && (!first_coeff_found ||
					      !second_coeff_found); i++){
	   if (indices[i] == index){
	      matind[0] = i;
	      first_coeff_found = TRUE;
	   }
	   if (indices[i] == (index + 2 * total_edgenum)){
	      matind[1] = i;
	      second_coeff_found = TRUE;
	   }
	}
#ifndef DIRECTED_X_VARS
	for (i = 0; i < varnum && !third_coeff_found; i++){
	   if (indices[i] == (index + total_edgenum)){
	      matind[2] = i;
	      third_coeff_found = TRUE;
	   }
	}
#endif
	if (first_coeff_found){
#ifdef DIRECTED_X_VARS
	   lhs += -values[matind[0]] * (vcp->capacity - demand);
#else
	   if (vcp->par.prob_type == CSTP || vcp->par.prob_type == CTP){
	      lhs += -values[matind[0]]*vcp->capacity;
	   }else{
	      lhs += -values[matind[0]]*vcp->capacity/2;
	   }
#endif
	   if (second_coeff_found){
	      if (third_coeff_found){
		 lhs += values[matind[1]];
		 lhs += values[matind[2]];
	      }else{
		 lhs += values[matind[1]];
	      }
	   }else if (third_coeff_found){
	      matind[1] = matind[2];
	      lhs += values[matind[1]];
	   }
	}else if (second_coeff_found){
	   matind[0] = matind[1];
	   lhs += values[matind[0]];
	   if (third_coeff_found){
	      matind[1] = matind[2];
	      lhs += values[matind[1]];
	   }
	}else if (third_coeff_found){
	   matind[0] = matind[2];
	   lhs += values[matind[0]];
	}
	*is_violated = (lhs > (double)(cut->rhs)+etol);
	*quality   = lhs - (double)cut->rhs;
	if (*quality < etol && *quality > -etol) *quality = 0;
	FREE(matind);
	return(USER_SUCCESS);
	
      case TIGHT_FLOW:

	if ((index = ((int *)coef)[0]) < total_edgenum){
	   v0 = edges[index << 1];
	   v1 = edges[(index << 1) + 1];
	}else{
	   v1 = edges[(index - total_edgenum) << 1];
	   v0 = edges[((index - total_edgenum) << 1) + 1];
	}

#ifdef DIRECTED_X_VARS
	d_x_vars = TRUE;
	for (k = 0; k < varnum; k++){
	   if (indices[k] == index){
	      lhs += values[k] * (v1 ? -vcp->demand[v1] : 0);
	      break;
	   }
	}
#else
	d_x_vars = FALSE;
	for (k = 0; k < varnum; k++){
	   if (indices[k] == (index < total_edgenum ? index :
				    index - total_edgenum)){
	      lhs += values[k] * (v1 ? -vcp->demand[v1] : 0);
	      break;
	   }
	}
#endif
	for (k = 0; k < varnum; k++){
	   if (indices[k] == index + (1 + d_x_vars) * total_edgenum){
	      lhs += values[k];
	      break;
	   }
	}
	/* This loop is done very inefficiently and should be rewritten */
	for (i = 0; i < v1; i++){
	   index = INDEX(i, v1) + (2 + d_x_vars) * total_edgenum;
	   for (k = 0; k < varnum; k++){
	      if (indices[k] == index){
		 lhs += -values[k];
		 break;
	      }
	   }
	}
	for (i = v1 + 1; i < vertnum; i++){
	   index = INDEX(i, v1) + (1 + d_x_vars) * total_edgenum;
	   for (k = 0; k < varnum; k++){
	      if (indices[k] == index){
		 lhs += -values[k];
		 break;
	      }
	   }
	}
	*is_violated = (lhs > (double)(cut->rhs)+etol);
	*quality   = lhs - (double)cut->rhs;
	if (*quality < etol && *quality > -etol) *quality = 0;
	return(USER_SUCCESS);
#endif

#ifdef DIRECTED_X_VARS
      case X_CUT:
	first_coeff_found = second_coeff_found = FALSE;
	for (i = 0; i < varnum && (!first_coeff_found ||
					      !second_coeff_found); i++){
	   if (indices[i] == ((int *)coef)[0]){
	      lhs += values[i];
	      first_coeff_found = TRUE;
	   }
	   if (indices[i] == ((int *)coef)[0]+total_edgenum){
	      lhs += values[i];
	      second_coeff_found = TRUE;
	   }
	}
	*is_violated = (lhs > (double)(cut->rhs)+etol);
	*quality   = lhs - (double)cut->rhs;
	if (*quality < etol && *quality > -etol) *quality = 0;
	return(USER_SUCCESS);
#endif

#if 0
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
#endif
      
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
   cnrp_spec_cp *vcp = (cnrp_spec_cp *)user;
   free_pool_net(vcp);

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function creates the solution graph from the current LP solution
\*===========================================================================*/

pool_net *create_pool_net(cnrp_spec_cp *vcp, int varnum, int *indices,
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
#ifdef DIRECTED_X_VARS   
   pool_edge *pedge;
   int total_edgenum = vertnum*(vertnum-1)/2;
   char edge_exists;
#endif
   
   n = (pool_net *) calloc (1, sizeof(pool_net));
   n->vertnum = vertnum;
   n->edgenum = varnum;
   n->verts = (pool_node *)calloc((int)vertnum, sizeof(pool_node));
   n->adjlist = (pool_edge *)calloc(2*(int)edgenum, sizeof(pool_edge));
   verts = n->verts;
   adjlist = n->adjlist;
  
   for (i = 0; i < varnum; i++){
#ifdef DIRECTED_X_VARS
      if (indices[i] < total_edgenum){
	 nv0 = edges[indices[i] << 1];
	 nv1 = edges[(indices[i] << 1) + 1];
      }else{
	 nv0 = edges[(indices[i]-total_edgenum) << 1];
	 nv1 = edges[((indices[i]-total_edgenum) << 1) + 1];
      }
      for (edge_exists = FALSE, pedge = verts[nv0].first; pedge;
	   pedge = pedge->next){
	 if (pedge->other_end == nv1){
	    pedge->weight += values[i];
	    for (pedge = verts[nv1].first; pedge; pedge = pedge->next){
	       if (pedge->other_end == nv0){
		  pedge->weight += values[i];
	       }
	    }
	    edge_exists = TRUE;
	    break;
	 }
      }
      if (edge_exists)
	 continue;
#else
      nv0 = edges[indices[i] << 1];
      nv1 = edges[(indices[i] << 1) + 1];
#endif
      
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

void free_pool_net(cnrp_spec_cp *vcp)
{
   if (vcp->n){
      FREE(vcp->n->adjlist);
      FREE(vcp->n->verts);
      FREE(vcp->n);
   }
}

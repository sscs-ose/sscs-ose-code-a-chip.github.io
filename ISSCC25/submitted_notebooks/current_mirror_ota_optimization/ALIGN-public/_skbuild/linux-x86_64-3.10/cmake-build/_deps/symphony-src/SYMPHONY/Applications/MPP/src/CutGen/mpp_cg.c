/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Mixed Postman Problem.                                                */
/*                                                                           */
/* (c) Copyright 2005-2007 Lehigh University. All Rights Reserved.           */
/*                                                                           */
/* This application was originally developed by Andrew Hofmann and was       */
/* modified by  Ted Ralphs (ted@lehigh.edu)                                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdlib.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_macros.h"
#include "sym_constants.h"
#include "sym_proccomm.h"
#include "sym_cg_u.h"

/* MPP include files */
#include "mpp.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains user-written functions used by the cut generator
 * process.
\*===========================================================================*/

/*===========================================================================*\
 * Here is where the user must receive all of the data sent from
 * user_send_cg_data() and set up data structures. Note that this function is
 * only called if one of COMPILE_IN_CG, COMPILE_IN_LP, or COMPILE_IN_TM is
 * FALSE.
\*===========================================================================*/

int user_receive_cg_data(void **user, int dg_id)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

int user_receive_lp_solution_cg(void *user)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/
/*===========================================================================*/

/*===========================================================================*\
 * Find cuts violated by a particular LP solution. This can be a fairly
 * involved function but the bottom line is that an LP solution comes in
 * and cuts go out. Remember, use the function cg_send_cut() to send cuts out
 * when they are found
\*===========================================================================*/

int user_find_cuts(void *user, int varnum, int iter_num, int level,
		   int index, double objval, int *indices, double *values,
		   double ub, double etol, int *cutnum, int *alloc_cuts,
		   cut_data ***cuts)
{
   /* heuristic 1 */
   mpp_problem *mpp = (mpp_problem *)user;
   int degree, delta = 0, odd_nodes, i, j, k, num_cuts = 0;
   int *odds;
   cut_data *new_cut = NULL;
   int storer = 0, counter = 0, cursor = 0;
   int new_node = 0, current_component = 0;

   int *stack, *node_visited, *component;
   double *holder;
   int *return_list, *cut_sizes;
   int **matrix;
   char *chararray; 
   double holder2;
   int exiter;
   /* calloc makes the rest 0 ? */
   
   odds = (int *) calloc(mpp->numnodes, sizeof(int));
   component = (int *) calloc(mpp->numnodes, sizeof(int));
   node_visited = (int *) calloc(mpp->numnodes, sizeof(int));
   
   holder = (double *) calloc(mpp->numedges*2+mpp->numarcs, sizeof(double));
   cut_sizes = (int *) calloc(mpp->numnodes, sizeof(int));
   matrix = (int **) calloc(mpp->numnodes, sizeof(int *));
   new_cut = (cut_data *) calloc(1, sizeof(cut_data));
   stack = (int *) calloc(mpp->numnodes, sizeof(int));
   return_list = (int *) calloc(mpp->numnodes, sizeof(int));
   for(i = 0; i <= mpp->numnodes - 1; i++){
      matrix[i] = (int *) calloc(mpp->numnodes, sizeof(int));
   }
   /* puts the current solution values into an easy to use array */
   /* make sure this for loop is right, might be varnum instead of varnum-1*/
   for (i = 0; i <= varnum - 1; i++){
      holder[indices[i]]=values[i];
   }
   for (j = 0; j <= mpp->numarcs - 1; j++){
      if (holder[j] > 1 + delta){
	 matrix[mpp->tail[j]][mpp->head[j]]=1;
	 matrix[mpp->head[j]][mpp->tail[j]]=1;
      }
   }
   /* check each edge to see if Xij +Xji >= 1 + delta */
   for (j = mpp->numarcs; j <= mpp->numedges + mpp->numarcs - 1; j++){			
      if (holder[j] + holder[mpp->numedges + j] > 1 + delta){
	 /* put tail[j] in head[j]'s ajacency list and vice versa */
	 matrix[mpp->tail[j]][mpp->head[j]] = 1;
	 matrix[mpp->head[j]][mpp->tail[j]] = 1;
      }
   }
	
   /* here we flag each node as odd or not odd */
   if (mpp->odd_checker == 0){
      mpp->is_odd = (int *) calloc(mpp->numnodes, sizeof(int));
      mpp->odd_checker=1;
      for (i = 0; i <= mpp->numnodes - 1; i++){
	 degree = 0;
	 
	 /* check each arc and edge to see if it is incident to each node*/
	 for (j = 0; j <= mpp->numarcs + mpp->numedges - 1; j++){
	    if((mpp->tail[j] == i) || (mpp->head[j] == i)){
	       degree++;
	    }
	 }
	 if(degree%2 == 1){
	    mpp->is_odd[i] = 1;
	 }else{
	    mpp->is_odd[i]=0;
	 }
      }
   }
   /* now we need to use a depth first search with a stack to find all the
      components of G' from the adjacency list and assign a number to each
      component */
   
   /* first make an adjacency matrix for graph g' */
#if 0
   for (i = 0; i <= mpp->numnodes - 1; i++){
      counter = 0;
      cursor = 0;
      if (node_visited[i] == 0){
	 if (mpp->is_odd[i] == 1){
	    odds[current_component]++;
	 }
	 node_visited[i] = 1;
	 stack[cursor] = i;
	 counter++;
	 exiter = 0;
	 while (new_node != 0 || cursor >= 0){
	    new_node = 0;
	    j = 0;
	    while (j <= mpp->numnodes - 1 && new_node == 0){
	       if(((matrix[stack[cursor]][j] == 1) ||
		   (matrix[j][stack[cursor]] == 1)) &&
		  (node_visited[j] == 0)){
		  if (mpp->is_odd[j] == 1)
		     odds[current_component]++;
		  new_node = 1;
		  exiter = 1;
		  node_visited[j] = 1;
		  cursor++;
		  stack[cursor] = j;
		  counter++;
	       }
	       j++;
	    }
	    if (new_node == 0){
	       component[stack[cursor]]=current_component;
	       cursor--;
	    }
	 }
	 cut_sizes[current_component]=counter;
	 current_component++;
      }
   }
   current_component--;
   for (i = current_component; i >= 0; i--){
      if (odds[i]%2 == 1 && cut_sizes[i] > 1){
	 counter = 0;
	 for(j = 0; j <= mpp->numnodes - 1; j++){
	    if (i == component[j]){
	       return_list[counter] = j;
	       counter++;
	    }
	 }
	 new_cut->coef  = (char*)return_list;
	 new_cut->size  = cut_sizes[i]*4;
	 new_cut->type  = ODD_CUT;
	 new_cut->sense ='G';
	 num_cuts += cg_send_cut(new_cut);
      }  
   }
   *cutnum = num_cuts;
#endif
   
   FREE(new_cut);
   FREE(holder);
   FREE(cut_sizes);
   for (i = 0; i <= mpp->numnodes - 1; i++){
      FREE(matrix[i]);
   }
   FREE(matrix);
   FREE(new_cut);
   FREE(stack);FREE(return_list);
   FREE(odds);
   FREE(node_visited);
   FREE(component); 
   
   return(USER_SUCCESS);
}
  
/*===========================================================================*/

/*===========================================================================*\
 * Free the user data structure
\*===========================================================================*/

int user_free_cg(void **user)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This is an undocumented (for now) debugging feature which can allow the user
 * to identify the cut which cuts off a particular known feasible solution.
\*===========================================================================*/

#ifdef CHECK_CUT_VALIDITY
int user_check_validity_of_cut(void *user, cut_data *new_cut)
{
  return(USER_DEFAULT);
}
#endif

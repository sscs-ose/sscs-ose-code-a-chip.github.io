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
#include <stdlib.h>
/*#include <sys/param.h>*/
#include <memory.h>
#include <math.h>

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_proccomm.h"
#include "sym_messages.h"
#include "sym_timemeas.h"
#include "sym_lp_u.h"
#include "sym_dg_params.h"

/* VRP include files */
#include "vrp_lp.h"
#include "vrp_dg_functions.h"
#include "vrp_macros.h"
#include "vrp_const.h"

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions for the LP process.
\*===========================================================================*/

/*===========================================================================*\
 * Here is where the user must receive all of the data sent from
 * user_send_lp_data() and set up data structures. Note that this function is
 * only called if one of COMPILE_IN_LP or COMPILE_IN_TM is FALSE.
\*===========================================================================*/

int user_receive_lp_data(void **user)
{
   vrp_lp_problem *vrp;
   int vertnum;
   int i, j, k, l;
   int total_edgenum;
   int zero_varnum, *zero_vars = NULL;

   vrp = (vrp_lp_problem *) calloc (1, sizeof(vrp_lp_problem));

   *user = (void *)vrp;

   receive_char_array((char *)(&vrp->par), sizeof(vrp_lp_params));
   receive_int_array(&vrp->window, 1);
   receive_int_array(&vrp->numroutes, 1);
   receive_int_array(&vrp->vertnum, 1);
   vertnum = vrp->vertnum;
   vrp->demand = (int *) calloc (vertnum, sizeof(int));
   receive_int_array(vrp->demand, (int)vertnum);
   receive_int_array(&vrp->capacity, 1);
   total_edgenum =  vertnum*(vertnum-1)/2;
   vrp->costs = (int *) calloc (total_edgenum, sizeof(int));
   receive_int_array(vrp->costs, total_edgenum);
   receive_int_array(&zero_varnum, 1);
   if (zero_varnum){
      zero_vars = (int *) malloc (zero_varnum*sizeof(int));
      receive_int_array(zero_vars, zero_varnum);
   }
   
   vrp->edges = (int *) calloc (2*total_edgenum, sizeof(int));

   /*create the edge list (we assume a complete graph) The edge is set to
     (0,0) in the edge list if it was eliminated in preprocessing*/
   for (i = 1, k = 0, l = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
	 if (l < zero_varnum && k == zero_vars[l]){
	    /*This is one of the zero edges*/
	    vrp->edges[2*k] = vrp->edges[2*k+1] = 0;
	    l++;
	    k++;
	    continue;
	 }
	 vrp->edges[2*k] = j;
	 vrp->edges[2*k+1] = i;
	 k++;
      }
   }
   FREE(zero_vars);

   vrp->cur_sol = (_node *) calloc (vrp->vertnum, sizeof(_node));
   if (vrp->window){
      copy_node_set(vrp->window, TRUE, (char *)"Original solution");
#if 0
      copy_node_set(vrp->window, TRUE, (char *)"Compressed solution");
#endif
   }
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here is where the user must create the initial LP relaxation for
 * each search node. See the comments below.
\*===========================================================================*/

int user_create_subproblem(void *user, int *indices, MIPdesc *mip, 
			   int *maxn, int *maxm, int *maxnz)
{
   vrp_lp_problem *vrp = (vrp_lp_problem *)user;
   int *costs = vrp->costs;
   int *edges = vrp->edges;
   int i;
   int total_edgenum = vrp->vertnum*(vrp->vertnum-1)/2;
   int cap_check = vrp->capacity*(vrp->numroutes-1);
   int total_demand = vrp->demand[0];
   
   /* set up the inital LP data */

   /* Our base constraints are that the sum of the weights of the
      edges adjacent to each node (except the depot) is 2. This means
      that each column will have exactly two nonzeros, one in each of
      the rows corresponding to its end points. Hence the total
      nonzeros is 2*n (n is the number of active variables). */
   mip->nz = 2 * mip->n;

   /* Estimate the maximum number of nonzeros (not needed, but helpful for
      efficiency*/
   *maxm = 2 * mip->m;
   *maxn = total_edgenum;
   *maxnz = mip->nz + ((*maxm) * (*maxn) / 10);

   /* Allocate the arrays. These are owned by SYMPHONY after returning. */
   mip->matbeg  = (int *) malloc((mip->n + 1) * ISIZE);
   mip->matind  = (int *) malloc((mip->nz) * ISIZE);
   mip->matval  = (double *) malloc((mip->nz) * DSIZE);
   mip->obj     = (double *) malloc(mip->n * DSIZE);
   mip->ub      = (double *) malloc(mip->n * DSIZE);
   mip->lb      = (double *) calloc(mip->n, DSIZE); /* zero lower bounds */
   mip->rhs     = (double *) malloc(mip->m * DSIZE);
   mip->sense   = (char *) malloc(mip->m * CSIZE);
   mip->rngval  = (double *) calloc(mip->m, DSIZE);
   mip->is_int  = (char *) calloc(mip->n, CSIZE);

   /* Fill out the appropriate data structures -- each column has
      exactly two entries */
   for (i = 0; i < mip->n; i++){
      mip->obj[i]        = (double) costs[indices[i]];
      mip->matbeg[i]     = 2*i;
      mip->matval[2*i]   = 1.0;
      mip->matval[2*i+1] = 1.0;
      mip->matind[2*i]   = edges[2*indices[i]];
      mip->matind[2*i+1] = edges[2*indices[i] + 1];
      mip->is_int[i]     = TRUE;
      
      /* Set the upper and lower bounds */
      if (edges[indices[i] << 1] == 0){
	 /*This is a depot edge and we have to check what its ub should be*/
	 /*Recall vrp->demand[0] == total_demand*/
	 if (total_demand - vrp->demand[edges[(indices[i] << 1) + 1]] >
	     cap_check)
	    /*in this case, the node cannot be on its own route*/
	    mip->ub[i] = 1;
	 else
	    mip->ub[i] = 2;
      }else{
	 mip->ub[i] = 1;
      }
   }
   mip->matbeg[mip->n] = 2*mip->n;
   
   /* set the initial right hand side */
   mip->rhs[0] = 2*vrp->numroutes;
   mip->sense[0] = 'E';
   for (i = vrp->vertnum - 1; i > 0; i--){
      mip->rhs[i]   = (double) 2;
      mip->sense[i] = 'E';
   }

   return(USER_SUCCESS);
}      


/*===========================================================================*/

/*===========================================================================*\
 * This function takes an LP solution and checks it for feasibility.
 * In our case, that means (1) it is integral (2) it is connected, and
 * (3) the routes obey the capacity constraints.
\*===========================================================================*/

int user_is_feasible(void *user, double lpetol, int varnum, int *indices,
		     double *values, int *feasible, double *true_objval,
		     char branching, double *heur_solution)
{
   vrp_lp_problem *vrp = (vrp_lp_problem *)user;
   vertex *verts;
   int *demand = vrp->demand, capacity = vrp->capacity;
   int rcnt, *compnodes, *compdemands;
   int vertnum = vrp->vertnum, i;
   network *n;
   double *compcuts;
   
   n = createnet(indices, values, varnum, lpetol, vrp->edges, demand, vertnum);
   
   if (!n->is_integral){
      *feasible = IP_INFEASIBLE;
      free_net(n);
      return(USER_SUCCESS);
   }
   
   verts = n->verts;
   compnodes = (int *) calloc (vertnum + 1, sizeof(int));
   compdemands = (int *) calloc (vertnum + 1, sizeof(int));
   compcuts = (double *) calloc (vertnum + 1, sizeof(double));
   /*get the components of the solution graph without the depot to check if the
     graph is connected or not*/
   rcnt = connected(n, compnodes, compdemands, NULL, compcuts, NULL);
   
   /*------------------------------------------------------------------------*\
    * For each component check to see if the cut it induces is nonzero -- each
    * component's cut value must be either 0 or 2 since we have integrality
   \*------------------------------------------------------------------------*/
   
   for (i = 0; i<rcnt; i++){
      if (compcuts[i+1] < lpetol || compdemands[i+1] > capacity){
	 *feasible = IP_INFEASIBLE;
	 FREE(compnodes);
	 FREE(compdemands);
	 FREE(compcuts);
	 free_net(n);
	 return(USER_SUCCESS);
      }
   }
   
   FREE(compnodes);
   FREE(compdemands);
   FREE(compcuts);
   
   *feasible = IP_FEASIBLE;
   
   construct_feasible_solution(vrp, n, true_objval);
   
   free_net(n);
   
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * In my case, a feasible solution is specified most compactly by
 * essentially a permutation of the customers along with routes numbers,
 * specifying the order of the customers on their routes. This is just
 * sent as a character array which then gets cast to an array of
 * structures, one for each customers specifying the route number and
 * the next customer on the route.
\*===========================================================================*/

int user_send_feasible_solution(void *user, double lpetol, int varnum,
				int *indices, double *values)
{
   vrp_lp_problem *vrp = (vrp_lp_problem *)user;

   send_char_array((char *)vrp->cur_sol, vrp->vertnum*sizeof(_node));

   return(USER_SUCCESS);
}


/*===========================================================================*/

/*===========================================================================*\
 * This function graphically displays the current fractional solution
 * This is done using the Interactie Graph Drawing program.
\*===========================================================================*/

int user_display_lp_solution(void *user, int which_sol, int varnum,
			     int *indices, double *values)
{
   vrp_lp_problem *vrp = (vrp_lp_problem *)user;

   if (vrp->par.verbosity > 10 ||
       (vrp->par.verbosity > 8 && (which_sol == DISP_FINAL_RELAXED_SOLUTION)) ||
       (vrp->par.verbosity > 6 && (which_sol == DISP_FEAS_SOLUTION))){
      display_support_graph(vrp->window, FALSE, (char *)"Original solution",
			    varnum, indices, values, .000001,
			    CTOI_WAIT_FOR_CLICK_AND_REPORT);
#if 0
      display_compressed_support_graph(vrp->window, FALSE,
				       (char *)"Compressed solution",
				       varnum, indices, values,
				       CTOI_WAIT_FOR_CLICK_AND_REPORT);
#endif
   }
   
   if (which_sol == DISP_FINAL_RELAXED_SOLUTION){
      return(DISP_NZ_INT);
   }else{
      return(USER_SUCCESS);
   }
}

/*===========================================================================*/

/*===========================================================================*\
 * You can add whatever information you want about a node to help you
 * recreate it. I don't have a use for it, but maybe you will.
\*===========================================================================*/

int user_add_to_desc(void *user, int *desc_size, char **desc)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Compare cuts to see if they are the same. We use the default, which
 * is just comparing byte by byte.
\*===========================================================================*/

int user_same_cuts(void *user, cut_data *cut1, cut_data *cut2, int *same_cuts)
{
   /*for now, we just compare byte by byte, as in the previous version of the
     code. Later, we might want to change this to be more efficient*/
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function receives a cut, unpacks it, and adds it to the set of
 * rows to be added to the LP.
\*===========================================================================*/

int user_unpack_cuts(void *user, int from, int type, int varnum,
		     var_desc **vars, int cutnum, cut_data **cuts,
		     int *new_row_num, waiting_row ***new_rows)
{
  int i, j, nzcnt = 0, nzcnt_side = 0, nzcnt_across = 0;
  int v0, v1, *edges = ((vrp_lp_problem *)user)->edges;
  waiting_row **row_list = NULL;
  int *matind = NULL, *matind_across, *matind_side;
  cut_data *cut;
  char *coef;
  double *matval = NULL;
  int jj, size, vertnum = ((vrp_lp_problem *)user)->vertnum; 
  int cliquecount = 0, val;
  char *clique_array;
  
  /*__BEGIN_EXPERIMENTAL_SECTION__*/
  int num_fracs, fracs;
  int  num_arcs, edge_index;
  char *cpt;
  int *arcs;
  char *indicators;
	
  double bigM, *weights;

  /*___END_EXPERIMENTAL_SECTION___*/
  *new_row_num = cutnum;
  if (cutnum > 0)
     *new_rows = row_list = (waiting_row **) calloc (cutnum,
						     sizeof(waiting_row *));

  for (j = 0; j < cutnum; j++){
     coef = (cut = cuts[j])->coef;
     cuts[j] = NULL;
     (row_list[j] = (waiting_row *) malloc(sizeof(waiting_row)))->cut = cut;
     switch (cut->type){
	/*-------------------------------------------------------------------*\
	 * The subtour elimination constraints are stored as a vector of
	 * bits indicating which side of the cut each customer is on
	\*-------------------------------------------------------------------*/

      case SUBTOUR_ELIM:
	matind_side = (int *) malloc(varnum * ISIZE);
	matind_across = (int *) malloc(varnum * ISIZE);
	for (i = 0, nzcnt = 0; i < varnum; i++){
	   v0 = edges[(vars[i]->userind) << 1];
	   v1 = edges[((vars[i]->userind) << 1) + 1];
	   if (coef[v0 >> DELETE_POWER] &
	       (1 << (v0 & DELETE_AND)) &&
	       (coef[v1 >> DELETE_POWER]) &
	       (1 << (v1 & DELETE_AND))){
	      matind_side[nzcnt_side++] = i;
	   }else if ((coef[v0 >> DELETE_POWER] >>
		      (v0 & DELETE_AND) & 1) ^
		     (coef[v1 >> DELETE_POWER] >>
		      (v1 & DELETE_AND) & 1)){
	      matind_across[nzcnt_across++] = i;
	   }
	}
	cut->type = nzcnt_side < nzcnt_across ? SUBTOUR_ELIM_SIDE :
	   SUBTOUR_ELIM_ACROSS;
	cut->deletable = TRUE;
	switch (cut->type){
	 case SUBTOUR_ELIM_SIDE:
	   row_list[j]->nzcnt = nzcnt_side;
	   row_list[j]->matind = matind_side;
	   cut->rhs = 0; /*RHS(compnodes[i+1],compdemands[i+1], capacity)*/
	   cut->sense = 'L';
	   FREE(matind_across);
	   break;
	   
	 case SUBTOUR_ELIM_ACROSS:
	   row_list[j]->nzcnt = nzcnt_across;
	   row_list[j]->matind = matind_across;
	   cut->rhs = 0; /*2*BINS(compdemands[i+1], capacity)*/
	   cut->sense = 'G';
	   FREE(matind_side);
	   break;
	}
	
	break;
       
	
      case SUBTOUR_ELIM_SIDE:
	matind = (int *) malloc(varnum * ISIZE);
	for (i = 0, nzcnt = 0; i < varnum; i++){
	   v0 = edges[(vars[i]->userind) << 1];
	   v1 = edges[((vars[i]->userind) << 1) + 1];
	   if (coef[v0 >> DELETE_POWER] &
	       (1 << (v0 & DELETE_AND)) &&
	       (coef[v1 >> DELETE_POWER]) &
	       (1 << (v1 & DELETE_AND))){
	      matind[nzcnt++] = i;
	   }
	}
	cut->deletable = TRUE;
	cut->sense = 'L';
	break;
	
      case SUBTOUR_ELIM_ACROSS:
	matind = (int *) malloc(varnum * ISIZE);
	for (i = 0, nzcnt = 0; i < varnum; i++){
	   v0 = edges[(vars[i]->userind) << 1];
	   v1 = edges[((vars[i]->userind) << 1) + 1];
	   if ((coef[v0 >> DELETE_POWER] >>
		(v0 & DELETE_AND) & 1) ^
	       (coef[v1 >> DELETE_POWER] >>
		(v1 & DELETE_AND) & 1)){
	      matind[nzcnt++] = i;
	   }
	}
	cut->deletable = TRUE;
	cut->sense = 'G';
	break;

      case CLIQUE:
	size = (vertnum >> DELETE_POWER) + 1;
	memcpy(&cliquecount, coef, ISIZE);
	matind = (int *) malloc(cliquecount*varnum*ISIZE);
	matval = (double *) malloc(cliquecount*varnum*DSIZE);
	coef += ISIZE;
	for (nzcnt = 0, i = 0; i < varnum; i++){
	   v0 = edges[(vars[i]->userind) << 1];
	   v1 = edges[((vars[i]->userind) << 1) + 1];
	   val = 0;
	   for (jj = 0; jj < cliquecount; jj++){
	      clique_array = coef + size * jj;
	      if (clique_array[v0 >> DELETE_POWER] &
		  (1 << (v0 & DELETE_AND)) &&
		  (clique_array[v1 >> DELETE_POWER]) &
		  (1 << (v1 & DELETE_AND))){
		 val += 1;
	      }
	   }
	   if (val){
	      matind[nzcnt] = i;
	      matval[nzcnt++] = val;
	   }
	}
	cut->deletable = TRUE;
	break;
	
      /*__BEGIN_EXPERIMENTAL_SECTION__*/
      case FARKAS:
	matind = (int *) malloc(varnum * ISIZE);
	matval = (double *) malloc(varnum * DSIZE);
	
	cpt = coef + ((vertnum >> DELETE_POWER) + 1); 
	memcpy((char *)&num_arcs, cpt, ISIZE);
	cpt += ISIZE;
	arcs = (int *) malloc(num_arcs * ISIZE);
	indicators = (char *) malloc(num_arcs);  
	memcpy((char *)arcs, cpt, num_arcs * ISIZE);
	cpt += num_arcs * ISIZE;
	memcpy(indicators, cpt, num_arcs);
	cpt += num_arcs;
	memcpy((char *)&num_fracs, cpt, ISIZE);
	cpt += ISIZE;
	weights = (double *) malloc((num_fracs + 1) * DSIZE);
	memcpy((char *)weights, cpt, (num_fracs + 1) * DSIZE);
	bigM = (*(double *)weights);
	weights++;
	
	for (fracs = 0, i = 0, nzcnt = 0; i < varnum; i++){
	   edge_index = vars[i]->userind;
	   v0 = edges[edge_index << 1];
	   v1 = edges[(edge_index << 1) + 1];
	   
	   if (isset(coef, v1) || isset(coef,v0)){
	      for (jj = 0; jj < num_arcs; jj++){
		 if (arcs[jj] == edge_index){
		    matval[nzcnt] = indicators[jj] ? -bigM : weights[fracs++];
		    break;
		 }
	      }
	      if (jj == num_arcs) matval[nzcnt] = bigM;
	      matind[nzcnt++] = i;
	   }
	}
	cut->sense = 'G';
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	--weights;
	FREE(indicators);
	FREE(arcs);
	FREE(weights);
	break;
	
      case NO_COLUMNS:
	matind = (int *) malloc(varnum * ISIZE);
	matval = (double *) malloc(varnum * DSIZE);
	cpt = coef + ((vertnum >> DELETE_POWER) + 1); 
	memcpy((char *)&num_arcs, cpt, ISIZE);
	cpt += ISIZE;
	arcs = (int *) calloc(num_arcs, ISIZE);
	indicators = (char *) malloc(num_arcs);  
	memcpy((char *)arcs, cpt, num_arcs * ISIZE);
	cpt += num_arcs * ISIZE;
	memcpy(indicators, cpt, num_arcs);
	
	for (i = 0, nzcnt = 0; i < varnum; i++){
	   edge_index = vars[i]->userind;
	   v0 = edges[edge_index << 1];
	   v1 = edges[(edge_index << 1) + 1];
	   
	   if (isset(coef, v1) || isset(coef, v0)){
	      for (jj = 0; jj < num_arcs; jj++){
		 if (arcs[jj] == edge_index){
		    matval[nzcnt] = (indicators[jj]) ? 1.0 : 0.0;
		    break;
		 }
	      }
	      if (jj == num_arcs) matval[nzcnt]= -1.0;
	      if (fabs(matval[nzcnt]) >.5) matind[nzcnt++] = i;
	   }
	}
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	cut->deletable = TRUE;
	cut->sense = 'L';
	FREE(indicators);
	FREE(arcs);
	break;

      case GENERAL_NONZEROS:
	cpt = coef;
	memcpy((char *)&num_arcs, cpt, ISIZE);
	cpt += ISIZE;
	matind = (int *) malloc(num_arcs * ISIZE);
	arcs = (int *) calloc(num_arcs, ISIZE);
	matval = (double *) malloc(num_arcs * DSIZE);
	weights = (double *) malloc(num_arcs * DSIZE);
	memcpy((char *)arcs, cpt, num_arcs * ISIZE);
	cpt += num_arcs * ISIZE;
	memcpy((char *)weights, cpt, num_arcs * DSIZE);
	
	for (i = 0, nzcnt = 0; i < varnum; i++){
	   for (jj = 0; jj < num_arcs; jj++){
	      if (arcs[jj] == (edge_index = vars[i]->userind)){
		 matind[nzcnt] = i;
		 matval[nzcnt++] = weights[jj];
		 break;
	      }
	   }
	}
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	cut->deletable = TRUE;
	FREE(weights);
	FREE(arcs);
	break;
      /*___END_EXPERIMENTAL_SECTION___*/
	
      default:
	 break;

     }
     
     row_list[j]->matind = matind =
	(int *) realloc((char *)matind, nzcnt*ISIZE);
     row_list[j]->nzcnt = nzcnt;
     /*__BEGIN_EXPERIMENTAL_SECTION__*/
     if (cut->type != CLIQUE && cut->type != FARKAS &&
	 cut->type != NO_COLUMNS && cut->type != GENERAL_NONZEROS){
     /*___END_EXPERIMENTAL_SECTION___*/
     /*UNCOMMENT FOR PRODUCTION CODE*/
#if 0
     if (cut->type != CLIQUE){
#endif
	row_list[j]->matval = matval = (double *) malloc(nzcnt * DSIZE);
	for (i = nzcnt-1; i >= 0; i--)
	   matval[i] = 1;
	cut->branch = ALLOWED_TO_BRANCH_ON;
     }else{
	row_list[j]->matval=(double *) realloc((char *)matval, nzcnt * DSIZE);
     }
  }

  return(USER_SUCCESS);
}

/*===========================================================================*/

int user_send_lp_solution(void *user, int varnum, var_desc **vars, double *x,
			  int where)
{
   return(SEND_NONZEROS);
}

/*===========================================================================*/

/*===========================================================================*\
 * This routine does logical fixing of variables
\*===========================================================================*/

int user_logical_fixing(void *user, int varnum, var_desc **vars, double *x,
			char *status, int *num_fixed)
{
   vrp_lp_problem *vrp = (vrp_lp_problem *)user;
   lp_net *lp_net;
   int *compdemands, capacity = vrp->capacity;
   int numchains = 0, v0, v1;
   lp_net_node *verts;
   int i;
   int *edges = vrp->edges;
   int fixed_num = 0;

   /*This routine could possibly be sped up by using pointers directly
     as in the min_cut routine */

   /*set up the graph induced by the edges fixed to one*/
   lp_net = create_lp_net(vrp, status, varnum, vars);

   verts = lp_net->verts;

   compdemands = (int *) calloc (varnum + 1, sizeof(int));

   /*get the connected components of the 1-edge graph*/
   numchains = vrp_lp_connected(lp_net, compdemands);

   for (i = 0; i < varnum; i++){
      if (!(status[i] & NOT_FIXED) || (status[i] & VARIABLE_BRANCHED_ON))
	 continue;
      v0 = edges[(vars[i]->userind) << 1];
      v1 = edges[((vars[i]->userind) << 1) + 1];
      if (!v0){
	 if (verts[0].degree == 2*(vrp->numroutes)){
	    /* if the depot has 2*numroutes edges adjacent to it fixed to one,
	       then we can eliminate all other edges adjacent to the depot
	       from the problem*/
	    status[i] = PERM_FIXED_TO_LB;
	    fixed_num++;
	 }
      }else if ((verts[v0].degree == 2) || (verts[v1].degree == 2)){
	 /* if a particular node has to fixed-to-one edges adjacent to it,
	    then we can	eliminate all other edges adjacent to that node from
	    the problem*/
	 fixed_num++;
	 status[i] = PERM_FIXED_TO_LB;
      }else if (verts[v0].comp == verts[v1].comp){
	 /*if two vertices are in the same component in the 1-edge graph, then
	   the edge between them can be eliminated from the problem*/
	 fixed_num++;
	 status[i] = PERM_FIXED_TO_LB;
      }else if (compdemands[verts[v0].comp] + compdemands[verts[v1].comp]
	       > capacity){
	 /*if the sum of the demands in two components of the 1-edge graph is
	   greater than the capacity of a truck, then these two components
	   cannot be linked and so any edge that goes bewtween them can be
	   eliminated from the problem*/
	 fixed_num++;
	 status[i] = PERM_FIXED_TO_LB;
      }
   }
   
   *num_fixed = fixed_num;

   free_lp_net(lp_net);

   free((char *)compdemands);

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function generates the 'next' column
\*===========================================================================*/

int user_generate_column(void *user, int generate_what, int cutnum,
			 cut_data **cuts, int prevind, int nextind,
			 int *real_nextind, double *colval, int *colind,
			 int *collen, double *obj, double *lb, double *ub)
{
   vrp_lp_problem *vrp = (vrp_lp_problem *)user;
   int vh, vl, i;
   int total_edgenum = vrp->vertnum*(vrp->vertnum-1)/2;

   switch (generate_what){
    case GENERATE_NEXTIND:
      /* Here we just have to generate the specified column. First, we
	 determine the endpoints */
      BOTH_ENDS(nextind, &vh, &vl);
      *real_nextind = nextind;
      break;
    case GENERATE_REAL_NEXTIND:
      /* In this case, we have to determine what the "real" next edge is*/
      *real_nextind = nextind;
      if (prevind >= total_edgenum-1){
	 *real_nextind = -1;
	 return(USER_SUCCESS);
      }else{
	 if (nextind == -1) nextind = total_edgenum;
	 /*first, cycle through the edges that were eliminated in the root*/
	 for (i = prevind + 1; i < nextind && !vrp->edges[(i<<1)+1]; i++);
	 /*now we should have the next nonzero edge*/
	 vl = vrp->edges[i << 1];
	 vh = vrp->edges[(i << 1) + 1];
      }
      if (i == nextind)
	 return(USER_SUCCESS);

      *real_nextind = i;
      break;
   }
   
   /* Now we just have to generate the column corresponding to (vh, vl) */

   {
      int nzcnt = 0, vertnum = vrp->vertnum;
      char *coef;
      cut_data *cut;
      int j, size;
      int cliquecount = 0, val;
      char *clique_array;

      /*__BEGIN_EXPERIMENTAL_SECTION__*/
      int num_arcs, edge_index;
      char *cpt; 
      int *arcs = (int *) calloc(total_edgenum, sizeof(int));
      double bigM, *weights = (double *) calloc(total_edgenum, sizeof(double));
      char *indicators = (char *) malloc(((vertnum*vertnum)/2)* sizeof(char));

      /*___END_EXPERIMENTAL_SECTION___*/
      colval[0] = 1;
      colind[0] = vl; /* supposes vl < vh !!!!!!**********/
      colval[1] = 1;
      colind[1] = vh;
      nzcnt = 2;

      /* The coefficient for each row depends on what kind of cut it
	 is */
      for (i = 0; i < cutnum; i++){
	 coef = (cut = cuts[i])->coef;
	 switch(cut->type){
	    
	  case SUBTOUR_ELIM_SIDE:
	    if (isset(coef, vh) && isset(coef, vl)){
	       colval[nzcnt] = 1;
	       colind[nzcnt++] = vertnum + i;
	    }
	    break;
	    
	  case SUBTOUR_ELIM_ACROSS:
	    /* It's important to have isclr here!!!!! see the macros */
	    if (isclr(coef, vh) ^ isclr(coef, vl)){
	       colval[nzcnt] = 1;
	       colind[nzcnt++] = vertnum + i;
	    }
	    break;
	    
	  case CLIQUE:
	    size = (vertnum >> DELETE_POWER) + 1;
	    memcpy(&cliquecount, coef, ISIZE);
	    coef += ISIZE;
	    val = 0;
	    for (j = 0; j < cliquecount; j++){
	       clique_array = coef + size * j;
	       if (isset(clique_array, vh) && isset(clique_array, vl))
		  val += 1;
	    }
	    if (val){
	       colval[nzcnt] = val;
	       colind[nzcnt++] = vertnum + i;
	    }
	    break;
	    
	  /*__BEGIN_EXPERIMENTAL_SECTION__*/
	  case FARKAS:
	    if (isset(coef, vh) || isset(coef,vl)){
	       cpt = coef + ((vertnum >> DELETE_POWER) + 1); 
	       memcpy((char *)&num_arcs, cpt, ISIZE);
	       memcpy((char *)arcs, cpt, ISIZE*(num_arcs + 1));
	       arcs++;
	       cpt += (ISIZE * (num_arcs + 1))/CSIZE;
	       memcpy((char *)weights, cpt, DSIZE*(num_arcs + 1));
	       bigM = (*(double *)weights);
	       weights++;
	       weights = (double *) calloc( total_edgenum, sizeof(double)) ;
	       edge_index = INDEX(vh, vl); 
		  
	       for (j = 0; j < num_arcs; j++){
		  if ( arcs[j] == edge_index){
		     colval[nzcnt] = weights[j];
		     break;
		  }
	       }
	       if (j == num_arcs) colval[nzcnt] = bigM;
	       colind[nzcnt++] = vertnum + i;
	       arcs--;
	       weights--;
	    }
	    break;
	    
	  case NO_COLUMNS:
	    if (isset(coef, vh) || isset(coef,vl)){
	       cpt=coef+ ((vertnum >> DELETE_POWER) + 1); 
	       memcpy((char *)&num_arcs, cpt, ISIZE);
	       cpt+= ISIZE /CSIZE;
	       memcpy((char *)arcs, cpt, ISIZE*(num_arcs));
	       cpt+=(ISIZE*(num_arcs ))/CSIZE;
	       memcpy((char *)indicators, cpt, CSIZE*(num_arcs));
	       edge_index=INDEX(vh, vl);
	       
	       for (j = 0; j < num_arcs; j++){
		  if ( arcs[j]==edge_index){
		     colval[nzcnt]=(indicators[j]) ? 1.0 : 0.0;
		     break;
		  }
	       }
	       if (j == num_arcs) colval[nzcnt] = -1.0;
	       if (fabs(colval[nzcnt]) >.5)  colind[nzcnt++] = i;
		
	    }
	    break;
	    
	  /*___END_EXPERIMENTAL_SECTION___*/
	  default:
	    printf("Unrecognized cut type %i!\n", cut->type);
	 }
	 
	 /* Set the upper and lower bounds */
	 if (vrp->edges[i << 1] == 0){
	    /*This is a depot edge and we have to check what its ub should be*/
	    /*Recall vrp->demand[0] == total_demand*/
	    if (vrp->demand[0] - vrp->demand[vrp->edges[(i << 1) + 1]] >
		vrp->capacity*(vrp->numroutes-1))
	       /*in this case, the node cannot be on its own route*/
	       *ub = 1;
	    else
	       *ub = 2;
	 }else{
	    *ub = 1;
	 }
	 *lb = 0;
      }
      *collen = nzcnt;
      *obj = vrp->costs[*real_nextind];
      /*__BEGIN_EXPERIMENTAL_SECTION__*/
      FREE(indicators);
      FREE(arcs);
      FREE(weights); 
      /*___END_EXPERIMENTAL_SECTION___*/
   }

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * You might want to print some statistics on the types and quantities
 * of cuts or something like that.
\*===========================================================================*/

int user_print_stat_on_cuts_added(void *user, int rownum, waiting_row **rows)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * You might want to eliminate rows from the local pool based on
 * knowledge of problem structure.
\*===========================================================================*/

int user_purge_waiting_rows(void *user, int rownum, waiting_row **rows,
			    char *delete_rows)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * The user has to generate the ubber bounds for the specified (non-base)
 * variables. Lower bounds are always assumed (w.l.o.g.) to be zero.
\*===========================================================================*/

/* Deprecated function */

#if 0
int user_get_upper_bounds(void *user, int varnum, int *indices, double *ub)
{
   vrp_lp_problem *vrp = (vrp_lp_problem *)user;
   int *edges = vrp->edges, i;
   int cap_check = vrp->capacity*(vrp->numroutes-1);
   int total_demand = vrp->demand[0];
   
   for (i = 0; i < varnum; i++){
      if (edges[indices[i] << 1] == 0){
	 /*This is a depot edge and we have to check what its ub should be*/
	 /*Recall vrp->demand[0] == total_demand*/
	 if (total_demand - vrp->demand[edges[(indices[i] << 1) + 1]] >
	     cap_check)
	    /*on this case, the node cannot be on its own route*/
	    ub[i] = 1;
	 else
	    ub[i] = 2;
      }else{
	 ub[i] = 1;
      }
   }
   
   return(USER_SUCCESS);
}
#endif

/*===========================================================================*/

/*===========================================================================*\
 * The user might want to generate cuts in the LP using information
 * about the current tableau, etc. This is for advanced users only.
\*===========================================================================*/

int user_generate_cuts_in_lp(void *user, LPdata *lp_data, int varnum,
			     var_desc **vars, double *x,
			     int *new_row_num, cut_data ***cuts)
{
   return(DO_NOT_GENERATE_CGL_CUTS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free all the user data structures
\*===========================================================================*/

int user_free_lp(void **user)
{
   vrp_lp_problem *vrp = (vrp_lp_problem *)(*user);

#ifndef COMPILE_IN_CG
   FREE(vrp->demand);
#endif
#if 0
   FREE(vrp->costs);
   FREE(vrp->edges);
   FREE(vrp->cur_sol);
   FREE(vrp);
#endif
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function creates a the network of fixed edges that is used in the
 * logical fixing routine 
\*===========================================================================*/

lp_net *create_lp_net(vrp_lp_problem *vrp, char *status, int edgenum,
		      var_desc **vars)
{
   lp_net *n;
   lp_net_node *verts;
   int nv0 = 0, nv1 = 0;
   lp_net_edge *adjlist;
   int vertnum = vrp->vertnum, i;
   int *demand = vrp->demand;
   int *edges = vrp->edges;

   n = (lp_net *) calloc (1, sizeof(lp_net));
   n->vertnum = vertnum;
   n->edgenum = vertnum*(vertnum-1)/2;
   n->verts = (lp_net_node *) calloc (n->vertnum, sizeof(lp_net_node));
   n->adjlist = (lp_net_edge *) calloc (2*(n->edgenum), sizeof(lp_net_edge));
   verts = n->verts;
   adjlist = n->adjlist;
  
   for (i = 0; i < edgenum; i++, status++){
      if (*status != PERM_FIXED_TO_UB)
	 continue;
      nv0 = edges[vars[i]->userind << 1];
      nv1 = edges[(vars[i]->userind << 1) +1];
      if (!verts[nv0].first){
	 verts[nv0].first = adjlist;
	 verts[nv0].degree += (int) vars[i]->ub;
      }
      else{
	 adjlist->next = verts[nv0].first;
	 verts[nv0].first = adjlist;
	 verts[nv0].degree += (int) vars[i]->ub;
      }
      adjlist->other_end = nv1;
      adjlist++;
      if (!verts[nv1].first){
	 verts[nv1].first = adjlist;
	 verts[nv1].degree += (int) vars[i]->ub;
      }
      else{
	 adjlist->next = verts[nv1].first;
	 verts[nv1].first = adjlist;
	 verts[nv1].degree += (int) vars[i]->ub;
      }
      adjlist->other_end = nv0;
      adjlist++;
   }
   
   for (i=0; i< vertnum; i++)
      verts[i].demand = demand[i];

   return(n);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function constructs the connected components of the 1-edges graph
 * used in the logical fixing routine 
\*===========================================================================*/

int vrp_lp_connected(lp_net *n, int *compdemands)
{
   int cur_node = 0, cur_comp = 0;
   lp_net_node *verts = n->verts;
   int vertnum = n->vertnum;
   lp_net_edge *cur_edge;
   int *nodes_to_scan, num_nodes_to_scan = 0;

   nodes_to_scan = (int *) calloc (vertnum, sizeof(int));

   while (TRUE){
      for (cur_node = 1; cur_node < vertnum; cur_node++)
	 if (!verts[cur_node].comp){ /* Look for the first node not already
					in a component */
	    break;
	 }

      if (cur_node == n->vertnum) break; /* we are done */

      nodes_to_scan[num_nodes_to_scan++] = cur_node;
      /* add the cur_node to the list of nodes to be scanned */
      verts[cur_node].comp = ++cur_comp;
      /* add the current node to the current component */
      compdemands[cur_comp] = verts[cur_node].demand;
      while(TRUE){
	 /* In each iteration of this loop, we take the next node off the
	    list of nodes to be scanned, add it to the current component, and
	    then add all its neighbors to the list of nodes to be scanned */
	 for (cur_node = nodes_to_scan[--num_nodes_to_scan],
	      verts[cur_node].scanned = TRUE,
	      cur_edge = verts[cur_node].first,
	      cur_comp = verts[cur_node].comp;
	      cur_edge; cur_edge = cur_edge->next){
	    if (cur_edge->other_end){
	       if (!verts[cur_edge->other_end].comp){
		  verts[cur_edge->other_end].comp = cur_comp;
		  compdemands[cur_comp] += verts[cur_edge->other_end].demand;
		  nodes_to_scan[num_nodes_to_scan++] = cur_edge->other_end;
	       }
	    }
	 }
	 if (!num_nodes_to_scan) break;
	 /* when there are no more nodes to scan, we start a new component */
      }
   }
   
   free((char *) nodes_to_scan);
   return(cur_comp);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free the data structures associated with the 1-edges graph
\*===========================================================================*/

void free_lp_net(lp_net *n)
{
  if (n){
    FREE(n->adjlist);
    FREE(n->verts);
    FREE(n);
  }
}

/*===========================================================================*/

void construct_feasible_solution(vrp_lp_problem *vrp, network *n,
				 double *true_objval)
{
   _node *tour = vrp->cur_sol;
   int cur_vert = 0, prev_vert = 0, cur_route, count;
   elist *cur_route_start = NULL;
   edge *edge_data;
   vertex *verts = n->verts;
   double cost = 0;
   
   /*construct the tour corresponding to this solution vector*/
   for (cur_route_start = verts[0].first, cur_route = 1, cost = 0,
	   edge_data = cur_route_start->data; cur_route <= vrp->numroutes;
	cur_route++){
      edge_data = cur_route_start->data;
      edge_data->scanned = TRUE;
      cur_vert = edge_data->v1;
      tour[prev_vert].next = cur_vert;
      tour[cur_vert].route = cur_route;
      prev_vert = 0;
      cost += vrp->costs[INDEX(prev_vert, cur_vert)];
      while (cur_vert){
	 if (verts[cur_vert].first->other_end != prev_vert){
	    prev_vert = cur_vert;
	    edge_data = verts[cur_vert].first->data;
	    cur_vert = verts[cur_vert].first->other_end;
	 }
	 else{
	    prev_vert = cur_vert;
	    edge_data = verts[cur_vert].last->data; /*This statement could
						      possibly be taken out to
						      speed things up a bit*/
	    cur_vert = verts[cur_vert].last->other_end;
	 }
	 tour[prev_vert].next = cur_vert;
	 tour[cur_vert].route = cur_route;
	 cost += vrp->costs[INDEX(prev_vert, cur_vert)];
      }
      edge_data->scanned = TRUE;
      
      while (cur_route_start->data->scanned){
	 if (!(cur_route_start = cur_route_start->next_edge)) break;
      }
   }
   *true_objval = cost;

   /* Display the solution */
   
   printf("\nSolution Found:\n");
   printf("Solution Cost: %.0f\n", cost);

   cur_vert = tour[0].next;
   
   if (tour[0].route == 1)
      printf("\n0 ");
   while (cur_vert != 0){
      if (tour[prev_vert].route != tour[cur_vert].route){
	 printf("\nRoute #%i: ", tour[cur_vert].route);
	 count = 0;
      }
      printf("%i ", cur_vert);
      count++;
      if (count > 15){
	 printf("\n");
	 count = 0;
      }
      prev_vert = cur_vert;
      cur_vert = tour[cur_vert].next;
   }
   printf("\n\n");
}

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef TRACE_PATH

#include "sym_lp.h"

void check_lp(lp_prob *p)
{
   LPdata *lp_data = p->lp_data;
   int i, j, l;
   tm_prob *tm = p->tm;
   double *x = (double *) malloc(tm->feas_sol_size * DSIZE), lhs, cost = 0;
   double *lhs_totals = (double *) calloc(lp_data->m, DSIZE);
   MakeMPS(lp_data, 0, 0);

   get_x(lp_data);

   printf("Optimal Fractional Solution: %.10f\n", lp_data->lpetol);
   for (i = 0; i < lp_data->n; i++){
      if (lp_data->x[i] > lp_data->lpetol){
	 printf("uind: %i colind: %i value: %.10f cost: %f\n",
		lp_data->vars[i]->userind, i, lp_data->x[i], lp_data->obj[i]);
      }
      cost += lp_data->obj[i]*lp_data->x[i];
   }
   printf("Cost: %f\n", cost);
   
   printf("\nFeasible Integer Solution:\n");
   for (cost = 0, i = 0; i < tm->feas_sol_size; i++){
      printf("uind: %i ", tm->feas_sol[i]);
      for (j = 0; j < lp_data->n; j++){
	 if (lp_data->vars[j]->userind == tm->feas_sol[i]){
	    cost += lp_data->obj[j];
	    printf("colind: %i lb: %f ub: %f obj: %f\n", j, lp_data->lb[j],
		   lp_data->ub[j], lp_data->obj[j]);
	    break;
	 }
      }
      if (j == lp_data->n)
	 printf("\n\nERROR!!!!!!!!!!!!!!!!\n\n");
      x[i] = 1.0;
   }
   printf("Cost: %f\n", cost);

   printf("\nChecking LP....\n\n");
   printf("Number of cuts: %i\n", lp_data->m);
   for (i = 0; i < tm->feas_sol_size; i++){
      for (j = 0; j < lp_data->n; j++){
	 if (tm->feas_sol[i] == lp_data->vars[j]->userind)
	    break;
      }
      for (l = lp_data->matbeg[j]; l < lp_data->matbeg[j] + lp_data->matcnt[j];
	   l++){
	 lhs_totals[lp_data->matind[l]] += 1;
      }
   }
   for (i = 0; i < p->base.cutnum; i++){
      printf("Cut %i: %f %c %f\n", i, lhs_totals[i], lp_data->sense[i],
	     lp_data->rhs[i]);
   }
   for (; i < lp_data->m; i++){
      lhs = compute_lhs(tm->feas_sol_size, tm->feas_sol, x,
				   lp_data->rows[i].cut, p->base.cutnum);
      printf("Cut %i: %f %f %c %f\n", i, lhs_totals[i], lhs, lp_data->sense[i],
	     lp_data->rhs[i]);
      if (lp_data->rows[i].cut->sense == 'G' ?
	  lhs < lp_data->rows[i].cut->rhs : lhs > lp_data->rows[i].cut->rhs){
	 printf("LP: ERROR -- row is violated by feasible solution!!!\n");
	 sleep(600);
	 exit(1);
      }
   }
}
#endif
/*___END_EXPERIMENTAL_SECTION___*/

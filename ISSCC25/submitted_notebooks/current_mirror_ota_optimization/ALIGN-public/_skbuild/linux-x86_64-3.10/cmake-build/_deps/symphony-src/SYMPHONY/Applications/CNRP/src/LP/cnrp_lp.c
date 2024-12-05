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
#ifdef MULTI_CRITERIA
#include "sym_cg_u.h"
#endif

/* CNRP include files */
#include "cnrp_lp.h"
#include "cnrp_dg_functions.h"
#include "cnrp_macros.h"
#include "cnrp_const.h"

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
   cnrp_spec *cnrp;
   int vertnum;
   int i, j, k, l;
   int total_edgenum;
   int zero_varnum, *zero_vars = NULL;

   cnrp = (cnrp_spec *) calloc (1, sizeof(cnrp_spec));

   *user = (void *)cnrp;

   receive_char_array((char *)(&cnrp->par), sizeof(cnrp_lp_params));
   receive_int_array(&cnrp->window, 1);
   receive_int_array(&cnrp->numroutes, 1);
   receive_int_array(&cnrp->vertnum, 1);
   vertnum = cnrp->vertnum;
   cnrp->demand = (double *) calloc (vertnum, sizeof(double));
   receive_dbl_array(cnrp->demand, vertnum);
   receive_dbl_array(&cnrp->capacity, 1);
   total_edgenum =  vertnum*(vertnum-1)/2;
   cnrp->costs = (int *) calloc (total_edgenum, sizeof(int));
   receive_int_array(cnrp->costs, total_edgenum);
   receive_int_array(&zero_varnum, 1);
   if (zero_varnum){
      zero_vars = (int *) malloc (zero_varnum*sizeof(int));
      receive_int_array(zero_vars, zero_varnum);
   }
   receive_dbl_array(&cnrp->utopia_fixed, 1);
   receive_dbl_array(&cnrp->utopia_variable, 1);
   receive_dbl_array(&cnrp->ub, 1);
 
   /* The one additional edge allocated is for the extra variable when finding
      nondominated solutions for multi-criteria problems */  
   cnrp->edges = (int *) calloc (2*(total_edgenum+1), sizeof(int));

   /* Create the edge list (we assume a complete graph) The edge is set to
      (0,0) in the edge list if it was eliminated in preprocessing*/
   for (i = 1, k = 0, l = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
	 if (l < zero_varnum && k == zero_vars[l]){
	    /*This is one of the zero edges*/
	    cnrp->edges[2*k] = cnrp->edges[2*k+1] = 0;
	    l++;
	    k++;
	    continue;
	 }
	 cnrp->edges[2*k] = j;
	 cnrp->edges[2*k+1] = i;
	 k++;
      }
   }
   cnrp->edges[2*total_edgenum] = cnrp->edges[2*total_edgenum + 1] = 0;
   FREE(zero_vars);

   if (cnrp->par.prob_type == VRP || cnrp->par.prob_type == TSP ||
       cnrp->par.prob_type == BPP){
      cnrp->cur_sol = (_node *) calloc (cnrp->vertnum, sizeof(_node));
   }else{
      cnrp->cur_sol_tree = (int *) calloc (cnrp->vertnum - 1, ISIZE);
   }

   cnrp->variable_cost = cnrp->fixed_cost = MAXDOUBLE;

/*__BEGIN_EXPERIMENTAL_SECTION__*/
   if (cnrp->window){
      copy_node_set(cnrp->window, TRUE, (char *)"Weighted solution");
      copy_node_set(cnrp->window, TRUE, (char *)"Flow solution");
   }

/*___END_EXPERIMENTAL_SECTION___*/
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free all the user data structures
\*===========================================================================*/

int user_free_lp(void **user)
{
   cnrp_spec *cnrp = (cnrp_spec *)(*user);
   
#if !(defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP))
   FREE(cnrp->demand);
   FREE(cnrp->costs);
   FREE(cnrp->edges);
#endif
   FREE(cnrp->cur_sol);
   FREE(cnrp->cur_sol_tree);
   FREE(cnrp);
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
   return(USER_DEFAULT);
   
   cnrp_spec *cnrp = (cnrp_spec *)user;
   int *costs = cnrp->costs;
   int *edges = cnrp->edges;
   int i, j, maxvars = 0;
   char resize = FALSE;
   int vertnum = cnrp->vertnum;
   int total_edgenum = vertnum*(vertnum-1)/2;
   char prob_type = cnrp->par.prob_type, od_const = FALSE, d_x_vars = FALSE;
   int v0, v1;
   double flow_capacity;
#ifdef ADD_CAP_CUTS 
   int basecutnum = (2 + od_const)*vertnum - 1 + 2*total_edgenum;
#elif defined(ADD_FLOW_VARS)
   int basecutnum = (2 + od_const)*vertnum - 1;
#else
   int basecutnum = (1 + od_const)*vertnum;
#endif
#ifdef ADD_X_CUTS
   basecutnum += total_edgenum;
#endif
#if defined(DIRECTED_X_VARS) && !defined(ADD_FLOW_VARS)
#ifdef FIND_NONDOMINATED_SOLUTIONS
   int edgenum = (mip->n - 1)/2;
#else
   int edgenum = (mip->n)/2;
#endif
#elif defined(ADD_FLOW_VARS)
#ifdef DIRECTED_X_VARS
#ifdef FIND_NONDOMINATED_SOLUTIONS
   int edgenum = (mip->n - 1)/4;
#else
   int edgenum = (mip->n)/4;
#endif

   flow_capacity = cnrp->capacity;
#else
#ifdef FIND_NONDOMINATED_SOLUTIONS
   int edgenum = (mip->n-1)/3;
#else
   int edgenum = (mip->n)/3;
#endif

   if (cnrp->par.prob_type == CSTP || cnrp->par.prob_type == CTP)
      flow_capacity = cnrp->capacity;
   else
      flow_capacity = cnrp->capacity/2;
#endif
#else
#ifdef FIND_NONDOMINATED_SOLUTIONS
   int edgenum = mip->n - 1;
#else
   int edgenum = mip->n;
#endif
#endif
   
   /* set up the inital LP data */

   /*Estimate the number of nonzeros*/
#ifdef ADD_CAP_CUTS
   mip->nz = 12*edgenum;
#elif defined(ADD_FLOW_VARS)
   mip->nz = 8*edgenum;
#else
   mip->nz = 3*edgenum;
#endif
#ifdef ADD_X_CUTS
   mip->nz += 2*edgenum;
#endif
#ifdef FIND_NONDOMINATED_SOLUTIONS
   mip->nz += mip->n + 1;
#endif
   *maxm = MAX(100, 3 * mip->m);
#ifdef ADD_FLOW_VARS
   *maxn = 3*total_edgenum;
#else
   *maxn = total_edgenum;
#endif
#ifdef DIRECTED_X_VARS
   *maxn += total_edgenum;
#endif
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

#ifdef DIRECTED_X_VARS
   /*whether or not we will have out-degree constraints*/
   od_const = (prob_type == VRP || prob_type == TSP || prob_type == BPP);
   d_x_vars = TRUE;
#endif
   
   for (i = 0, j = 0; i < mip->n; i++){
#ifdef FIND_NONDOMINATED_SOLUTIONS
      if (indices[i] == mip->n - 1){
	 mip->is_int[i]    = FALSE;
	 mip->ub[i]        = MAXINT;
	 mip->matbeg[i]    = j;
	 mip->obj[i]       = 1.0;
	 mip->matval[j]    = -1.0;
	 mip->matind[j++]  = basecutnum;
	 mip->matval[j]    = -1.0;
	 mip->matind[j++]  = basecutnum + 1;
	 continue;
      }
#endif
      if (indices[i] < total_edgenum){
	 mip->is_int[i]    = TRUE;
	 mip->ub[i]        = 1.0;
	 mip->matbeg[i]    = j;
#ifdef FIND_NONDOMINATED_SOLUTIONS
	 mip->obj[i]       = cnrp->par.rho*((double) costs[indices[i]]);
	 mip->matval[j]    = cnrp->par.gamma*((double) costs[indices[i]]);
	 mip->matind[j++]  = basecutnum;
#else
	 mip->obj[i]       = cnrp->par.gamma*((double) costs[indices[i]]);
#endif
	 if (prob_type == CSTP || prob_type == CTP){
	    /*cardinality constraint*/
	    mip->matind[j] = 0;
	    mip->matval[j++] = 1.0;
	 }
	 /*in-degree constraint*/
	 mip->matval[j]    = 1.0;
	 mip->matind[j++]  = edges[2*indices[i]+1];
#ifdef DIRECTED_X_VARS
	 /*out-degree constraint*/
	 if (od_const){
	    mip->matval[j]   = 1.0;
	    mip->matind[j++] = vertnum + edges[2*indices[i]];
	 }
#else
	 if (prob_type == VRP || prob_type == TSP ||
	     prob_type == BPP || edges[2*indices[i]]){
	    mip->matval[j]   = 1.0;
	    mip->matind[j++] = edges[2*indices[i]];
	 }
#endif	 
#ifdef ADD_CAP_CUTS
	 v0 = edges[2*indices[i]];
	 mip->matval[j]    = -flow_capacity + (v0 ? cnrp->demand[v0] : 0);
	 mip->matind[j++]  = (2 + od_const)*vertnum - 1 + indices[i];
#ifndef DIRECTED_X_VARS
	 mip->matval[j]    = -flow_capacity +
	    cnrp->demand[edges[2*indices[i] + 1]];
	 mip->matind[j++]  = 2*cnrp->vertnum - 1 + total_edgenum +
	    indices[i];
#endif
#endif
#ifdef ADD_X_CUTS
	 mip->matval[j]    = 1.0;
	 mip->matind[j++]  = (2 + od_const)*vertnum-1 + 2*total_edgenum +
	    indices[i];
#endif
#ifdef DIRECTED_X_VARS
      }else if (indices[i] < 2*total_edgenum){
	 mip->is_int[i]    = TRUE;
	 mip->ub[i]        = 1.0;
	 mip->matbeg[i]    = j;
#ifdef FIND_NONDOMINATED_SOLUTIONS
	 mip->obj[i]       = cnrp->par.rho*((double) costs[indices[i] -
							  total_edgenum]);
	 mip->matval[j]    = cnrp->par.gamma*((double) costs[indices[i] -
							    total_edgenum]);
	 mip->matind[j++]  = basecutnum;
#else
	 mip->obj[i]       = cnrp->par.gamma*((double)costs[indices[i] -
							  total_edgenum]);
#endif
	 if (prob_type == CSTP || prob_type == CTP){
	    /*cardinality constraint*/
	    mip->matind[j] = 0;
	    mip->matval[j++] = 1.0;
	 }
	 /*in-degree constraint*/
	 if (od_const || edges[2*(indices[i] - total_edgenum)]){
	    mip->matval[j]   = 1.0;
	    mip->matind[j++] = edges[2*(indices[i] - total_edgenum)];
	 }
	 /*out-degree constraint*/
	 if (od_const){
	    mip->matval[j]    = 1.0;
	    mip->matind[j++]  = vertnum + edges[2*(indices[i] -
						   total_edgenum)+1];
	 }
#ifdef ADD_CAP_CUTS
	 mip->matval[j]    = -flow_capacity +
	    cnrp->demand[edges[2*(indices[i] - total_edgenum) + 1]];
	 mip->matind[j++]  = (2 + od_const)*vertnum - 1 + indices[i];
#endif
#ifdef ADD_X_CUTS
	 mip->matval[j]    = 1.0;
	 mip->matind[j++]  = (2 + od_const)*vertnum-1 + 2*total_edgenum +
	    indices[i] - total_edgenum;
#endif
#endif
      }else if (indices[i] < (2+d_x_vars)*total_edgenum){
	 mip->is_int[i] = FALSE;
	 v0 = edges[2*(indices[i]-(1+d_x_vars)*total_edgenum)];
	 mip->ub[i] = flow_capacity - (v0 ? cnrp->demand[v0] : 0);
	 mip->matbeg[i]    = j;
#ifdef FIND_NONDOMINATED_SOLUTIONS
	 mip->obj[i]       = cnrp->par.rho*((double) costs[indices[i] -
					(1+d_x_vars)*total_edgenum]);
	 mip->matval[j]    = cnrp->par.tau*((double) costs[indices[i]-
					(1+d_x_vars)*total_edgenum]);
	 mip->matind[j++]  = basecutnum + 1;
#else
	 mip->obj[i]       =
	    cnrp->par.tau*((double) costs[indices[i]-
					(1+d_x_vars)*total_edgenum]);
#endif
#ifdef ADD_CAP_CUTS
	 mip->matval[j]    = 1.0;
	 mip->matval[j+1]  = 1.0;
	 if (edges[2*(indices[i]-(1+d_x_vars)*total_edgenum)])
	    mip->matval[j+2] = -1.0;
	 mip->matind[j++]  = (2 + od_const)*vertnum - 1 + indices[i] -
	    (1+d_x_vars)*total_edgenum;
	 mip->matind[j++]  = (1+od_const)*vertnum + edges[2*(indices[i] -
				(1+d_x_vars)*total_edgenum) + 1] - 1;
	 if (edges[2*(indices[i] - (1+d_x_vars)*total_edgenum)])
	    mip->matind[j++] = (1+od_const)*vertnum + edges[2*(indices[i] -
				(1+d_x_vars)*total_edgenum)] - 1;
#else
	 mip->matval[j]  = 1.0;
	 if (edges[2*(indices[i]-(1+d_x_vars)*total_edgenum)])
	    mip->matval[j+1] = -1.0;
	 mip->matind[j++]  = (1+od_const)*vertnum + edges[2*(indices[i] -
				(1+d_x_vars)*total_edgenum) + 1] - 1;
	 if (edges[2*(indices[i] - (1+d_x_vars)*total_edgenum)])
	    mip->matind[j++] = (1+od_const)*vertnum + edges[2*(indices[i] -
				(1+d_x_vars)*total_edgenum)] - 1;
#endif	 
      }else{
	 mip->is_int[i] = FALSE;
	 v1 = edges[2*(indices[i]-(2+d_x_vars)*total_edgenum) + 1];
	 mip->ub[i] = flow_capacity - cnrp->demand[v1];
	 mip->matbeg[i]    = j;
#ifdef FIND_NONDOMINATED_SOLUTIONS
	 mip->obj[i]       = cnrp->par.rho*((double) costs[indices[i] -
					(2+d_x_vars)*total_edgenum]);
	 mip->matval[j]    = cnrp->par.tau*((double) costs[indices[i]-
					(2+d_x_vars)*total_edgenum]);
	 mip->matind[j++]  = basecutnum + 1;
#else
	 mip->obj[i]       =
	    cnrp->par.tau*((double) costs[indices[i]-
					(2+d_x_vars)*total_edgenum]);
#endif
#ifdef ADD_CAP_CUTS
	 mip->matval[j]    = 1.0;
	 mip->matval[j+1]  = -1.0;
	 if (edges[2*(indices[i] - (2+d_x_vars)*total_edgenum)])
	    mip->matval[j+2] = 1.0;
	 mip->matind[j++]  = (2+od_const)*vertnum - 1 + indices[i] -
	    (1+d_x_vars)*total_edgenum;
	 mip->matind[j++]  = (1+od_const)*vertnum + edges[2*(indices[i] -
				(2+d_x_vars)*total_edgenum)+1] - 1;
	 if (edges[2*(indices[i] - (2+d_x_vars)*total_edgenum)])
	    mip->matind[j++] = (1+od_const)*vertnum + edges[2*(indices[i] -
				(2+d_x_vars)*total_edgenum)] - 1;
#else
	 mip->matval[j]  = -1.0;
	 if (edges[2*(indices[i] - (2+d_x_vars)*total_edgenum)])
	    mip->matval[j+1] = 1.0;
	 mip->matind[j++]  = (1+od_const)*vertnum + edges[2*(indices[i] -
				(2+d_x_vars)*total_edgenum)+1] - 1;
	 if (edges[2*(indices[i] - (2+d_x_vars)*total_edgenum)])
	    mip->matind[j++] = (1+od_const)*vertnum + edges[2*(indices[i] -
				(2+d_x_vars)*total_edgenum)] - 1;
#endif
      }
   }
   mip->matbeg[i] = j;
   
   /* set the initial right hand side */
   if (od_const){
      /*degree constraints for the depot*/
#if 0
      mip->rhs[0] = cnrp->numroutes;
      mip->sense[0] = 'E';
      mip->rhs[vertnum] = cnrp->numroutes;
      mip->sense[vertnum] = 'E';
#else
      mip->rhs[0] = 1.0;
      mip->sense[0] = 'G';
      mip->rhs[vertnum] = 1.0;
      mip->sense[vertnum] = 'G';
#endif      
   }else if (prob_type == VRP || prob_type == TSP || prob_type == BPP){
      (mip->rhs[0]) = 2*cnrp->numroutes;
      mip->sense[0] = 'E';
   }else{
      /*cardinality constraint*/
      mip->rhs[0] = vertnum - 1;
      mip->sense[0] = 'E';
   }
   for (i = vertnum - 1; i > 0; i--){
      switch (prob_type){
       case VRP:
       case TSP:
       case BPP:
	 if (od_const){
	    mip->rhs[i] = 1.0;
	    mip->sense[i] = 'E';
	    mip->rhs[i+vertnum] = 1.0;
	    mip->sense[i+vertnum] = 'E';
	 }else{
	    mip->rhs[i] = 2.0;
	    mip->sense[i] = 'E';
	 }
	 break;
       case CSTP:
       case CTP:
	 mip->rhs[i] = 1.0;
#ifdef DIRECTED_X_VARS
	 mip->sense[i] = 'E';
#else
	 mip->sense[i] = 'G';
#endif
	 break;
      }
#ifdef ADD_FLOW_VARS
      mip->rhs[(1+od_const)*vertnum + i - 1] = cnrp->demand[i];
      mip->sense[(1+od_const)*vertnum + i - 1] = 'E';
#endif
   }
#ifdef ADD_CAP_CUTS
   for (i = (2+od_const)*vertnum - 1;
	i < (2+od_const)*vertnum - 1 + 2*total_edgenum; i++){
      mip->rhs[i] = 0.0;
      mip->sense[i] = 'L';
   }
#endif
#ifdef ADD_X_CUTS
   for (i = (2+od_const)*vertnum-1+2*total_edgenum;
	i < (2+od_const)*vertnum-1+3*total_edgenum; i++){
      mip->rhs[i] = 1;
      mip->sense[i] = 'L';
   }
#endif
#ifdef FIND_NONDOMINATED_SOLUTIONS
   mip->rhs[basecutnum] = cnrp->par.gamma*cnrp->utopia_fixed;   
   mip->sense[basecutnum] = 'L';
   mip->rhs[basecutnum+1] = cnrp->par.tau*cnrp->utopia_variable;   
   mip->sense[basecutnum+1] = 'L';
#endif
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
   cnrp_spec *cnrp = (cnrp_spec *)user;
   vertex *verts;
   double *demand = cnrp->demand, capacity = cnrp->capacity, *compdemands;
   int rcnt, *compnodes;
   int vertnum = cnrp->vertnum, i, x_varnum;
   network *n;
   double *compcuts;
   int total_edgenum = vertnum*(vertnum - 1)/2;
   double fixed_cost = 0.0, variable_cost = 0.0;
#ifdef DIRECTED_X_VARS
   char d_x_vars = TRUE;
#else
   char d_x_vars = FALSE;
#endif
   
#ifdef ADD_FLOW_VARS
   int tmp = varnum;
   edge* edge1;
   double flow_value, real_demand;
   
#ifndef ADD_CAP_CUTS
      n = create_flow_net(indices, values, varnum, lpetol, cnrp->edges, demand,
			  vertnum);
#else
#ifdef DIRECTED_X_VARS
   for (x_varnum = 0; x_varnum < varnum && indices[x_varnum] < 2*total_edgenum;
	x_varnum++);
#else
   for (x_varnum = 0; x_varnum < varnum && indices[x_varnum] < total_edgenum;
	x_varnum++);
#endif   
   
   n = create_net(indices, values, x_varnum, lpetol, cnrp->edges, demand,
		  vertnum);
#endif   
#else
   n = create_net(indices, values, x_varnum, lpetol, cnrp->edges, demand,
		  vertnum);
#endif
   
   if (!n->is_integral){
      *feasible = IP_INFEASIBLE;
      free_net(n);
      return(USER_SUCCESS);
   }

#if defined(ADD_FLOW_VARS) && !defined(ADD_CAP_CUTS)
#ifdef DIRECTED_X_VARS
   for (i = 0, edge1 = n->edges; i < n->edgenum; i++, edge1++){
      if ((flow_value = edge1->flow1) > lpetol){
	 real_demand = edge1->v0 ? demand[edge1->v0] : 0;
	 if ((capacity - real_demand)*edge1->weight1 < edge1->flow1 -
	     lpetol){
	    *feasible = IP_INFEASIBLE;
	    free_net(n);
	    return(USER_SUCCESS);
	 }
      }
      if ((flow_value = edge1->flow2) > lpetol){
	 if ((capacity-demand[edge1->v1])*edge1->weight2<edge1->flow2 -
	     lpetol){
	    *feasible = IP_INFEASIBLE;
	    free_net(n);
	    return(USER_SUCCESS);
	 }
      }
   }
#else
   for (i = 0, edge1 = n->edges; i < n->edgenum; i++, edge1++){
      if (capacity*edge1->weight < edge1->flow1 + edge1->flow2 - lpetol){
	 *feasible = IP_INFEASIBLE;
	 free_net(n);
	 return(USER_SUCCESS);
      }
   }
#endif
#endif
   
   verts = n->verts;
   compnodes = (int *) calloc (vertnum + 1, sizeof(int));
   compdemands = (double *) calloc (vertnum + 1, sizeof(double));
   compcuts = (double *) calloc (vertnum + 1, sizeof(double));
   /*get the components of the solution graph without the depot to check if the
     graph is connected or not*/
#if defined(ADD_FLOW_VARS) && !defined(ADD_CAP_CUTS)
   rcnt = flow_connected(n, compnodes, compdemands, NULL, compcuts, NULL, lpetol);
#else
   rcnt = connected(n, compnodes, compdemands, NULL, compcuts, NULL);
#endif
   
   /*------------------------------------------------------------------------*\
    * For each component check to see if the cut it induces is nonzero.
    * Depending on the problem type, each component's cut value
    * must be either 0, 1, or 2 since we have integrality
   \*------------------------------------------------------------------------*/
   
   for (i = 0; i < rcnt; i++){
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
   
   if (cnrp->par.verbosity > 5){
      display_support_graph(cnrp->window, FALSE, (char *)"Weighted solution",
			    x_varnum, indices, values, .000001, total_edgenum,
			    FALSE);
#ifdef ADD_FLOW_VARS
      display_support_graph_flow(cnrp->window, FALSE, (char *)"Flow solution",
				 tmp, x_varnum, indices, values, .000001,
				 total_edgenum,CTOI_WAIT_FOR_CLICK_AND_REPORT);
#endif
   }

#if defined(MULTI_CRITERIA) && defined(FIND_NONDOMINATED_SOLUTIONS) && 0
   if (construct_feasible_solution(cnrp, n, true_objval, lpetol,
				   branching) > 0){
      *feasible = IP_FEASIBLE_BUT_CONTINUE;
   }else{
      *feasible = IP_FEASIBLE;
   }
#else
   *feasible = IP_FEASIBLE;
#endif
   
   free_net(n);

   return (USER_SUCCESS);
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
   cnrp_spec *cnrp = (cnrp_spec *)user;

   if (cnrp->par.prob_type == TSP || cnrp->par.prob_type == VRP ||
       cnrp->par.prob_type == BPP)
      send_char_array((char *)cnrp->cur_sol, cnrp->vertnum*sizeof(_node));
   else
      send_int_array(cnrp->cur_sol_tree, (cnrp->vertnum-1) * ISIZE);
      
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
   cnrp_spec *cnrp = (cnrp_spec *)user;
   int i, total_edgenum = cnrp->vertnum*(cnrp->vertnum -1)/2;
   
#ifdef ADD_FLOW_VARS
   for (i = 0; i < varnum && indices[i] < 2*total_edgenum; i++);
#endif   
   
   if (cnrp->par.verbosity > 10 ||
       (cnrp->par.verbosity > 8 && (which_sol == DISP_FINAL_RELAXED_SOLUTION))
       || (cnrp->par.verbosity > 6 && (which_sol == DISP_FEAS_SOLUTION))){
      display_support_graph(cnrp->window, FALSE, (char *)"Weighted solution",
			    i, indices, values, .000001, total_edgenum, FALSE);
      display_support_graph_flow(cnrp->window, FALSE, (char *)"Flow solution",
				 varnum, i, indices, values, .000001,
				 total_edgenum,CTOI_WAIT_FOR_CLICK_AND_REPORT);
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
  int i, j, k, nzcnt = 0, nzcnt_side = 0, nzcnt_across = 0;
  cnrp_spec *cnrp = (cnrp_spec *)user;
  int index, v0, v1, *edges = cnrp->edges;
  double demand;
  waiting_row **row_list = NULL;
  int *matind = NULL, *matind_across, *matind_side;
  cut_data *cut;
  char *coef;
  double *matval = NULL;
  int total_edgenum = cnrp->vertnum*(cnrp->vertnum - 1)/2;
  int size, vertnum = ((cnrp_spec *)user)->vertnum; 
  int cliquecount = 0, val, edgeind;
  char *clique_array, first_coeff_found, second_coeff_found, third_coeff_found;
#ifdef DIRECTED_X_VARS
  char d_x_vars = TRUE;
#else
  char d_x_vars = FALSE;
#endif
#if defined(ADD_FLOW_VARS) && defined(DIRECTED_X_VARS)
  int  numarcs, *arcs;
  char *coef2;
#endif
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

#if 0
      case SUBTOUR_ELIM:
	matind_side = (int *) malloc(varnum * ISIZE);
	matind_across = (int *) malloc(varnum * ISIZE);
	for (i = 0, nzcnt = 0; i < varnum; i++){
#ifdef ADD_FLOW_VARS
#ifdef DIRECTED_X_VARS
	   if (vars[i]->userind < 2*total_edgenum){
	      if (vars[i]->userind >= total_edgenum){
		 edgeind = vars[i]->userind - total_edgenum;
	      }else{
		 edgeind = vars[i]->userind;
	      }
#else
	   if ((edgeind = vars[i]->userind) < total_edgenum){   
#endif
#else
#ifdef DIRECTED_X_VARS
	   {
	      if (vars[i]->userind >= total_edgenum){
		 edgeind = vars[i]->userind - total_edgenum;
	      }else{
		 edgeind = vars[i]->userind;
	      }
#else	      
           {
	      edgeind = vars[i]->userind;
#endif
#endif
	      v0 = edges[edgeind << 1];
	      v1 = edges[(edgeind << 1) + 1];
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
#endif
      case SUBTOUR_ELIM:
      case SUBTOUR_ELIM_SIDE:
	matind = (int *) malloc(varnum * ISIZE);
	for (i = 0, nzcnt = 0; i < varnum; i++){
#ifdef DIRECTED_X_VARS
	   if (vars[i]->userind < 2*total_edgenum){
	      if (vars[i]->userind >= total_edgenum){
		 edgeind = vars[i]->userind - total_edgenum;
	      }else{
		 edgeind = vars[i]->userind;
	      }
#else
	   if ((edgeind = vars[i]->userind) < total_edgenum){   
#endif
	      v0 = edges[edgeind << 1];
	      v1 = edges[(edgeind << 1) + 1];
	      if (coef[v0 >> DELETE_POWER] & (1 << (v0 & DELETE_AND)) &&
		  (coef[v1 >> DELETE_POWER]) & (1 << (v1 & DELETE_AND))){
		 matind[nzcnt++] = i;
	      }
	   }
	}
	cut->sense = 'L';
	cut->deletable = TRUE;
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	break;
	
      case SUBTOUR_ELIM_ACROSS:
	matind = (int *) malloc(varnum * ISIZE);
	for (i = 0, nzcnt = 0; i < varnum; i++){
#ifdef DIRECTED_X_VARS
	   if (vars[i]->userind < 2*total_edgenum){
	      if (vars[i]->userind >= total_edgenum){
		 edgeind = vars[i]->userind - total_edgenum;
		 v1 = edges[edgeind << 1];
		 v0 = edges[(edgeind << 1) + 1];
	      }else{
		 edgeind = vars[i]->userind;
		 v0 = edges[edgeind << 1];
		 v1 = edges[(edgeind << 1) + 1];
	      }
	      if ((coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1) &&
		  !(coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1)){
		 matind[nzcnt++] = i;
	      }
	   }
#else
	   if (vars[i]->userind < total_edgenum){   
	      edgeind = vars[i]->userind;
	      v0 = edges[edgeind << 1];
	      v1 = edges[(edgeind << 1) + 1];
	      if ((coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1) ^
		  (coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1)){
		 matind[nzcnt++] = i;
	      }
	   }
#endif
	}
	cut->sense = 'G';
	cut->deletable = TRUE;
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	break;

#if defined(ADD_FLOW_VARS) && defined(DIRECTED_X_VARS)
      case MIXED_DICUT:
	matind = (int *) malloc(varnum * ISIZE);
	matval = (double *) malloc(varnum*DSIZE);
	demand = ((double *)coef)[0];
	numarcs = ((int *)(coef + DSIZE))[0];
	/* Array of the nodes in the set S */
	coef2 = coef + DSIZE + ISIZE;
	/* Array of the arcs in the set C */
	arcs = (int *) (coef + DSIZE + ISIZE + (vertnum >> DELETE_POWER)+1); 
	for (i = 0, nzcnt = 0; i < varnum; i++){
	   if (vars[i]->userind < 2*total_edgenum){
	      if (vars[i]->userind >= total_edgenum){
		 edgeind = vars[i]->userind - total_edgenum;
		 v1 = edges[edgeind << 1];
		 v0 = edges[(edgeind << 1) + 1];
	      }else{
		 edgeind = vars[i]->userind;
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
		    matind[nzcnt] = i;
		    matval[nzcnt++] = MIN(cnrp->capacity, demand);
		 }
	      }
	   }else{
	      if (vars[i]->userind < 3*total_edgenum){
		 edgeind = vars[i]->userind - 2*total_edgenum;
		 v0 = edges[edgeind << 1];
		 v1 = edges[(edgeind << 1) + 1];
	      }else{
		 edgeind = vars[i]->userind - 3*total_edgenum;
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
		    matind[nzcnt] = i;
		    matval[nzcnt++] = 1.0;
		 }
	      }
	   }
	}
	cut->sense = 'G';
	cut->deletable = TRUE;
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	break;
#endif
	
#ifdef ADD_FLOW_VARS
      case FLOW_CAP:
	matind = (int *)    malloc(3 * ISIZE);
	matval = (double *) malloc(3 * DSIZE);

	index = ((int *)coef)[0];
	v0 = index < total_edgenum ? edges[index << 1] :
	   edges[(index - total_edgenum) << 1];
	v1 = index < total_edgenum ? edges[(index << 1) + 1] :
	   edges[((index - total_edgenum) << 1) + 1];
	if (v0){
	   demand =
	      index < total_edgenum ? cnrp->demand[v0] : cnrp->demand[v1];
	}else{
	   demand = 0;
	}
	
	first_coeff_found = second_coeff_found = third_coeff_found = FALSE;
	for (i = 0; i < varnum && (!first_coeff_found ||
					      !second_coeff_found); i++){
	   if (vars[i]->userind == index){
	      matind[0] = i;
	      first_coeff_found = TRUE;
	   }
	   if (vars[i]->userind == (index + 2 * total_edgenum)){
	      matind[1] = i;
	      second_coeff_found = TRUE;
	   }
	}
#ifndef DIRECTED_X_VARS
	for (i = 0; i < varnum && !third_coeff_found; i++){
	   if (vars[i]->userind == (index + total_edgenum)){
	      matind[2] = i;
	      third_coeff_found = TRUE;
	   }
	}
#endif
	if (first_coeff_found){
#ifdef DIRECTED_X_VARS
	   matval[0] = -(cnrp->capacity - demand);
#else
	   if (cnrp->par.prob_type == CSTP || cnrp->par.prob_type == CTP){
	      matval[0] = -cnrp->capacity;
	   }else{
	      matval[0] = -cnrp->capacity/2;
	   }
#endif
	   if (second_coeff_found){
	      if (third_coeff_found){
		 matval[1] = matval[2] = 1.0;
		 nzcnt = 3;
	      }else{
		 matval[1] = 1.0;
		 nzcnt = 2;
	      }
	   }else if (third_coeff_found){
	      matind[1] = matind[2];
	      matval[1] = 1.0;
	      nzcnt = 2;
	   }else{
	      nzcnt = 0;
	   }
	}else if (second_coeff_found){
	   matind[0] = matind[1];
	   matval[0] = 1.0;
	   if (third_coeff_found){
	      matind[1] = matind[2];
	      matval[1] = 1.0;
	      nzcnt = 2;
	   }else{
	      nzcnt = 1;
	   }
	}else if (third_coeff_found){
	   matind[0] = matind[2];
	   matval[0] = 1.0;
	   nzcnt = 1;
	}else{
	   nzcnt = 0;
	}
	cut->sense = 'L';
	cut->deletable = FALSE;
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	break;

      case TIGHT_FLOW:

	matind = (int *)    malloc((vertnum + 1) * ISIZE);
	matval = (double *) malloc((vertnum + 1) * DSIZE);

	if ((index = ((int *)coef)[0]) < total_edgenum){
	   v0 = edges[index << 1];
	   v1 = edges[(index << 1) + 1];
	}else{
	   v1 = edges[(index - total_edgenum) << 1];
	   v0 = edges[((index - total_edgenum) << 1) + 1];
	}

#ifdef DIRECTED_X_VARS
	for (nzcnt = 0, k = 0; k < varnum; k++){
	   if (vars[k]->userind == index){
	      matind[nzcnt] = k;
	      matval[nzcnt++] = v1 ? -cnrp->demand[v1] : 0;
	      break;
	   }
	}
#else
	for (nzcnt = 0, k = 0; k < varnum; k++){
	   if (vars[k]->userind == (index < total_edgenum ? index :
				    index - total_edgenum)){
	      matind[nzcnt] = k;
	      matval[nzcnt++] = v1 ? -cnrp->demand[v1] : 0;
	      break;
	   }
	}
#endif
	for (k = 0; k < varnum; k++){
	   if (vars[k]->userind == index + (1 + d_x_vars) * total_edgenum){
	      matind[nzcnt] = k;
	      matval[nzcnt++] = 1.0;
	      break;
	   }
	}
	/* This loop is done very inefficiently and should be rewritten */
	for (i = 0; i < v1; i++){
	   index = INDEX(i, v1) + (2 + d_x_vars) * total_edgenum;
	   for (k = 0; k < varnum; k++){
	      if (vars[k]->userind == index){
		 matind[nzcnt] = k;
		 matval[nzcnt++] = -1.0;
		 break;
	      }
	   }
	}
	for (i = v1 + 1; i < vertnum; i++){
	   index = INDEX(i, v1) + (1 + d_x_vars) * total_edgenum;
	   for (k = 0; k < varnum; k++){
	      if (vars[k]->userind == index){
		 matind[nzcnt] = k;
		 matval[nzcnt++] = -1.0;
		 break;
	      }
	   }
	}
	cut->sense = 'L';
	cut->deletable = FALSE;
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	   
	break;
#endif

#ifdef DIRECTED_X_VARS
      case X_CUT:
	matind = (int *)    malloc(2 * ISIZE);
	matval = (double *) malloc(2 * DSIZE);
	first_coeff_found = second_coeff_found = FALSE;
	for (i = 0, nzcnt = 0; i < varnum && (!first_coeff_found ||
					      !second_coeff_found); i++){
	   if (vars[i]->userind == ((int *)coef)[0]){
	      matind[0] = i;
	      first_coeff_found = TRUE;
	   }
	   if (vars[i]->userind == ((int *)coef)[0]+total_edgenum){
	      matind[1] = i;
	      second_coeff_found = TRUE;
	   }
	}
	if (!first_coeff_found || !second_coeff_found){
	   printf("ERROR constructing X Cut!!\n\n");
	   nzcnt = 0;
	}else{
	   matval[0] = matval[1] = 1.0;
	   nzcnt = 2;
	}
	cut->sense = 'L';
	cut->deletable = FALSE;
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	break;
#endif

      case OPTIMALITY_CUT_FIXED:
	matind = (int *) malloc (varnum * ISIZE);
	matval =  (double *) malloc (varnum * DSIZE);
	for (nzcnt = 0, i = 0; i < varnum; i++){
	   if (vars[i]->userind < total_edgenum){
	      matind[nzcnt] = i;
	      matval[nzcnt++] = cnrp->costs[vars[i]->userind];
	   }
#ifdef DIRECTED_X_VARS
	   else if (vars[i]->userind < 2*total_edgenum){
	      matind[nzcnt] = i;
	      matval[nzcnt++] = cnrp->costs[vars[i]->userind - total_edgenum];
	   }
#endif
	}
	cut->sense = 'L';
	cut->deletable = FALSE;
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	break;
	
      case OPTIMALITY_CUT_VARIABLE:
	matind = (int *) malloc (varnum * ISIZE);
	matval =  (double *) malloc (varnum * DSIZE);
	for (nzcnt = 0, i = 0; i < varnum; i++){
	   if (vars[i]->userind >= (1 + d_x_vars) * total_edgenum &&
	       vars[i]->userind < (3 + d_x_vars) * total_edgenum){
	      matind[nzcnt] = i;
	      if (vars[i]->userind < (2 + d_x_vars) * total_edgenum){
		 matval[nzcnt++] =
		    cnrp->costs[vars[i]->userind-(1+d_x_vars) * total_edgenum];
	      }else{
		 matval[nzcnt++] =
		    cnrp->costs[vars[i]->userind-(2+d_x_vars) * total_edgenum];
	      }
	   }
	}
	cut->sense = 'L';
	cut->deletable = FALSE;
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	break;

      case CLIQUE:
	size = (vertnum >> DELETE_POWER) + 1;
	memcpy(&cliquecount, coef, ISIZE);
	matind = (int *) malloc(cliquecount*varnum*ISIZE);
	matval = (double *) malloc(cliquecount*varnum*DSIZE);
	coef += ISIZE;
	for (nzcnt = 0, i = 0; i < varnum; i++){
#ifdef ADD_FLOW_VARS
#ifdef DIRECTED_X_VARS
	   if (vars[i]->userind < 2*total_edgenum){
	      if (vars[i]->userind >= total_edgenum){
		 edgeind = vars[i]->userind - total_edgenum;
	      }else{
		 edgeind = vars[i]->userind;
	      }
#else
	   if ((edgeind = vars[i]->userind) < total_edgenum){   
#endif
#else
#ifdef DIRECTED_X_VARS
	   {
	      if (vars[i]->userind >= total_edgenum){
		 edgeind = vars[i]->userind - total_edgenum;
	      }else{
		 edgeind = vars[i]->userind;
	      }
#else	      
           {
	      edgeind = vars[i]->userind;
#endif
#endif
	      v0 = edges[edgeind << 1];
	      v1 = edges[(edgeind << 1) + 1];
	      val = 0;
	      for (k = 0; k < cliquecount; k++){
		 clique_array = coef + size * k;
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
	}
	cut->branch = DO_NOT_BRANCH_ON_THIS_ROW;
	cut->deletable = TRUE;
	break;
	
      default:
	printf("Unrecognized cut type %i!\n", cut->type);
     }
     
     row_list[j]->matind = matind =
	(int *) realloc((char *)matind, nzcnt*ISIZE);
     row_list[j]->nzcnt = nzcnt;
     if (cut->type == SUBTOUR_ELIM || cut->type == SUBTOUR_ELIM_ACROSS ||
	 cut->type == SUBTOUR_ELIM_SIDE){
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
   cnrp_spec *cnrp = (cnrp_spec *)user;
   lp_net *lp_net;
   double *compdemands, capacity = cnrp->capacity;
   int numchains = 0, v0, v1;
   lp_net_node *verts;
   int i;
   int *edges = cnrp->edges;
   int fixed_num = 0;
#ifdef ADD_FLOW_VARS
   int total_edgenum = cnrp->vertnum*(cnrp->vertnum - 1)/2;
#endif

   return(USER_SUCCESS); /*for now, don't do logical fixing*/
   
   /*This routine could possibly be sped up by using pointers directly
     as in the min_cut routine */

   /*set up the graph induced by the edges fixed to one*/
   lp_net = create_lp_net(cnrp, status, varnum, vars);

   verts = lp_net->verts;

   compdemands = (double *) calloc (varnum + 1, sizeof(double));

   /*get the connected components of the 1-edge graph*/
   numchains = cnrp_lp_connected(lp_net, compdemands);

#ifdef ADD_FLOW_VARS
   for (i = 0; i < varnum && vars[i]->userind < total_edgenum; i++){
#else
   for (i = 0; i < varnum; i++){
#endif
      if (!(status[i] & NOT_FIXED) || (status[i] & VARIABLE_BRANCHED_ON))
	 continue;
      v0 = edges[(vars[i]->userind) << 1];
      v1 = edges[((vars[i]->userind) << 1) + 1];
      if (!v0){
	 if (verts[0].degree == 2*(cnrp->numroutes)){
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

   FREE(compdemands);

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
   cnrp_spec *cnrp = (cnrp_spec *)user;
   int vh, vl, i;
   int total_edgenum = cnrp->vertnum*(cnrp->vertnum-1)/2;

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
	 for (i = prevind + 1; i < nextind && !cnrp->edges[(i<<1)+1]; i++);
	 /*now we should have the next nonzero edge*/
	 vl = cnrp->edges[i << 1];
	 vh = cnrp->edges[(i << 1) + 1];
      }
      if (i == nextind)
	 return(USER_SUCCESS);

      *real_nextind = i;
      break;
   }
   
   /* Now we just have to generate the column corresponding to (vh, vl) */

   {
      int nzcnt = 0, vertnum = cnrp->vertnum;
      char *coef;
      cut_data *cut;
      int j, size;
      int cliquecount = 0, val;
      char *clique_array;

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
	    
	  default:
	    printf("Unrecognized cut type %i!\n", cut->type);
	 }
      }
      *collen = nzcnt;
      *obj = cnrp->costs[*real_nextind];
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
 * The user might want to generate cuts in the LP using information
 * about the current tableau, etc. This is for advanced users only.
\*===========================================================================*/

int user_generate_cuts_in_lp(void *user, LPdata *lp_data, int varnum,
			     var_desc **vars, double *x,
			     int *new_row_num, cut_data ***cuts)
{
   return(GENERATE_CGL_CUTS);
}

/*===========================================================================*/

/*===========================================================================*\
 * This function creates a the network of fixed edges that is used in the
 * logical fixing routine 
\*===========================================================================*/

lp_net *create_lp_net(cnrp_spec *cnrp, char *status, int edgenum,
		      var_desc **vars)
{
   lp_net *n;
   lp_net_node *verts;
   int nv0 = 0, nv1 = 0;
   lp_net_edge *adjlist;
   int vertnum = cnrp->vertnum, i;
   double *demand = cnrp->demand;
   int *edges = cnrp->edges;
#ifdef ADD_FLOW_VARS
   int total_edgenum = vertnum*(vertnum-1)/2;
#endif
   
   n = (lp_net *) calloc (1, sizeof(lp_net));
   n->vertnum = vertnum;
   n->edgenum = vertnum*(vertnum-1)/2;
   n->verts = (lp_net_node *) calloc (n->vertnum, sizeof(lp_net_node));
   n->adjlist = (lp_net_edge *) calloc (2*(n->edgenum), sizeof(lp_net_edge));
   verts = n->verts;
   adjlist = n->adjlist;
  
#ifdef ADD_FLOW_VARS
   for (i = 0; i < edgenum && vars[i]->userind < total_edgenum; i++, status++){
#else
   for (i = 0; i < edgenum; i++, status++){
#endif      
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

int cnrp_lp_connected(lp_net *n, double *compdemands)
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

#if 0
char construct_feasible_solution(cnrp_spec *cnrp, network *n,
				 double *true_objval, double etol,
				 char branching)
{
  _node *tour = cnrp->cur_sol;
  int cur_vert = 0, prev_vert = 0, cur_route, i, count;
  elist *cur_route_start = NULL;
  edge *edge_data;
  vertex *verts = n->verts;
  double fixed_cost = 0.0, variable_cost = 0.0;
  int cuts = 0;
  char print_solution = FALSE;
  char continue_with_node = FALSE;
  
#ifdef MULTI_CRITERIA
  for (i = 0; i < n->edgenum; i++){
     fixed_cost += cnrp->costs[INDEX(n->edges[i].v0, n->edges[i].v1)];
#ifdef ADD_FLOW_VARS
     variable_cost += (n->edges[i].flow1+n->edges[i].flow2)*
	cnrp->costs[INDEX(n->edges[i].v0, n->edges[i].v1)];
#endif
  }

#if 0
  *true_objval -= cnrp->par.rho*(fixed_cost+variable_cost);
#endif
  
  if (cnrp->ub > 0 &&
      *true_objval-cnrp->par.rho*(fixed_cost+variable_cost) > cnrp->ub+etol){
     return(FALSE);
  }

  if (cnrp->par.gamma == 1.0){
     if (fixed_cost < cnrp->fixed_cost + etol){
	 if (fixed_cost < cnrp->fixed_cost - etol ||
	     (fixed_cost >= cnrp->fixed_cost - etol
	      && variable_cost < cnrp->variable_cost - etol)){
	    printf("\nBetter Solution Found:\n");
#ifdef ADD_FLOW_VARS
	    printf("Solution Fixed Cost: %.1f\n", fixed_cost);
	    printf("Solution Variable Cost: %.1f\n", variable_cost);
#else
	    printf("Solution Cost: %.0f\n", fixed_cost);
#endif
	    cnrp->variable_cost = variable_cost;
	    cnrp->fixed_cost = fixed_cost;
	    cnrp->ub = *true_objval-cnrp->par.rho*(fixed_cost+variable_cost);
	    print_solution = TRUE;
	 }
	/* Add an optimality cut for the second objective */
	 if (!branching){
	    cut_data *new_cut = (cut_data *) calloc(1, sizeof(cut_data));
	    new_cut->coef = NULL;
	    new_cut->rhs = (int) (variable_cost + etol) - 1;
	    new_cut->size = 0;
	    new_cut->type = OPTIMALITY_CUT_VARIABLE;
	    new_cut->name = CUT__DO_NOT_SEND_TO_CP;
	    continue_with_node = cg_send_cut(new_cut);
	    FREE(new_cut);
	 }else{
	    continue_with_node = TRUE;
	 }
     }
  }else if (cnrp->par.tau == 1.0){
     if (variable_cost < cnrp->variable_cost + etol){
	if (variable_cost < cnrp->variable_cost - etol ||
	    (variable_cost >= cnrp->variable_cost - etol
	     && fixed_cost < cnrp->fixed_cost - etol)){
	   printf("\nBetter Solution Found:\n");
#ifdef ADD_FLOW_VARS
	   printf("Solution Fixed Cost: %.1f\n", fixed_cost);
	   printf("Solution Variable Cost: %.1f\n", variable_cost);
#else
	   printf("Solution Cost: %.0f\n", fixed_cost);
#endif
	   cnrp->variable_cost = variable_cost;
	   cnrp->fixed_cost = fixed_cost;
	   cnrp->ub = *true_objval-cnrp->par.rho*(fixed_cost+variable_cost);
	   print_solution = TRUE;
	}
	/* Add an optimality cut for the second objective */
	if (!branching){
	   cut_data *new_cut = (cut_data *) calloc(1, sizeof(cut_data));
	   new_cut->coef = NULL;
	   new_cut->rhs = (int) (fixed_cost + etol) - 1;
	   new_cut->size = 0;
	   new_cut->type = OPTIMALITY_CUT_FIXED;
	   new_cut->name = CUT__DO_NOT_SEND_TO_CP;
	   continue_with_node = cg_send_cut(new_cut);
	   FREE(new_cut);
	}else{
	   continue_with_node = TRUE;
	}
     }
  }else{
     if ((*true_objval-cnrp->par.rho*(fixed_cost+variable_cost) <
	  cnrp->ub - etol) ||
	 (fixed_cost < cnrp->fixed_cost - etol &&
	  variable_cost < cnrp->variable_cost + etol) ||
	 (variable_cost < cnrp->variable_cost - etol &&
	  fixed_cost < cnrp->fixed_cost + etol)){
	printf("\nBetter Solution Found:\n");
#ifdef ADD_FLOW_VARS
	printf("Solution Fixed Cost: %.1f\n", fixed_cost);
	printf("Solution Variable Cost: %.1f\n", variable_cost);
#else
	printf("Solution Cost: %.0f\n", fixed_cost);
#endif
	cnrp->variable_cost = variable_cost;
	cnrp->fixed_cost = fixed_cost;
	cnrp->ub = *true_objval-cnrp->par.rho*(fixed_cost+variable_cost);
	print_solution = TRUE;
     }
     if (!branching){
	if (cnrp->par.gamma*(fixed_cost - cnrp->utopia_fixed) >
	    *true_objval-cnrp->par.rho*(fixed_cost+variable_cost)-etol){
	   /* Add an optimality cut for the second objective */
	   cut_data *new_cut = (cut_data *) calloc(1, sizeof(cut_data));
	   new_cut->coef = NULL;
	   new_cut->rhs = (int) (variable_cost + etol) - 1;
	   new_cut->size = 0;
	   new_cut->type = OPTIMALITY_CUT_VARIABLE;
	   new_cut->name = CUT__DO_NOT_SEND_TO_CP;
	   continue_with_node = cg_send_cut(new_cut);
	   FREE(new_cut);
	}else{
	   /* Add an optimality cut for the second objective */
	   cut_data *new_cut = (cut_data *) calloc(1, sizeof(cut_data));
	   new_cut->coef = NULL;
	   new_cut->rhs = (int) (fixed_cost + etol) - 1;
	   new_cut->size = 0;
	   new_cut->type = OPTIMALITY_CUT_FIXED;
	   new_cut->name = CUT__DO_NOT_SEND_TO_CP;
	   continue_with_node = cg_send_cut(new_cut);
	   FREE(new_cut);
	}
     }else{
	continue_with_node = TRUE;
     }
  }
#endif

  if (!print_solution){
     return(continue_with_node);
  }
     
  
  if (cnrp->par.prob_type == TSP || cnrp->par.prob_type == VRP ||
      cnrp->par.prob_type == BPP){ 
     /*construct the tour corresponding to this solution vector*/
     for (cur_route_start = verts[0].first, cur_route = 1,
	     edge_data = cur_route_start->data; cur_route <= cnrp->numroutes;
	  cur_route++){
	edge_data = cur_route_start->data;
	edge_data->scanned = TRUE;
	cur_vert = edge_data->v1;
	tour[prev_vert].next = cur_vert;
	tour[cur_vert].route = cur_route;
	prev_vert = 0;
	while (cur_vert){
	   if (verts[cur_vert].first->other_end != prev_vert){
	      prev_vert = cur_vert;
	      edge_data = verts[cur_vert].first->data;
	      cur_vert = verts[cur_vert].first->other_end;
	   }
	   else{
	      prev_vert = cur_vert;
	      edge_data = verts[cur_vert].last->data; /*This statement
							could possibly
							be taken out to speed
							things up a bit*/
	      cur_vert = verts[cur_vert].last->other_end;
	   }
	   tour[prev_vert].next = cur_vert;
	   tour[cur_vert].route = cur_route;
	}
	edge_data->scanned = TRUE;
	
	while (cur_route_start->data->scanned){
	   if (!(cur_route_start = cur_route_start->next_edge)) break;
	}
     }

     /* Display the solution */
   
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
  }else{
     for (i = 0; i < n->edgenum; i++){
	cnrp->cur_sol_tree[i] = INDEX(n->edges[i].v0, n->edges[i].v1);
     }

     /* Display the solution */
   
     for (i = 0; i < n->edgenum; i++){
	printf("%i %i\n", n->edges[i].v0, n->edges[i].v1);
     }
  }

  return(continue_with_node);
}
#endif

/*===========================================================================*/

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

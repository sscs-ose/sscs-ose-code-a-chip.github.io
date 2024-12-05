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
#include <string.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

/* SYMPHONY include files */
#include "sym_macros.h"
#include "symphony.h"
#include "sym_master.h"

/* CNRP include files */
#include "cnrp_const.h"
#include "cnrp_types.h"
#include "cnrp_io.h"
#include "cnrp_master_functions.h"
#include "small_graph.h"

void cnrp_load_problem(sym_environment *env, cnrp_problem *cnrp);

int cnrp_test(sym_environment *env);

/*===========================================================================*\
 * This is main() for the CNRP application
\*===========================================================================*/

int main(int argc, char **argv)
{
   /* Allocate the data structure to store the problem-specific data */
   cnrp_problem *cnrp = (cnrp_problem *) calloc(1, sizeof(cnrp_problem));
   double ub;
   char *pf;

   /* Open the SYMPHONY environemt */
   sym_environment *env = sym_open_environment();

   /* Print version info */
   sym_version();
   
   /* Parse the command line arguments */
   sym_parse_command_line(env, argc, argv);

  /* Tell SYMPHONY where the user data is stored, so that this pointer can be
      made available for user callbacks. */
   sym_set_user_data(env, cnrp);

   /* Read parameters from a file if there is one */
   sym_get_str_param(env, "param_file", &pf);
   cnrp_readparams(cnrp, pf, argc, argv);
   cnrp->par.base_variable_selection = SOME_ARE_BASE;
   
   sym_set_dbl_param(env, "granularity", .999999);
   
   if(cnrp->par.test){
     
     cnrp_test(env);
     
   } else {
     
     /* Read in the data */
     cnrp_io(cnrp, cnrp->par.infile);
     
     /* Read in a sparse graph representation of the network from a file */
     if (cnrp->par.use_small_graph == LOAD_SMALL_GRAPH){
       read_small_graph(cnrp);
     }
     
     if (!cnrp->numroutes && cnrp->par.prob_type == VRP){
       printf("\nError: Number of trucks not specified or computed "
	      "for VRP\n\n");
       exit(1);
     }
     
     if (cnrp->numroutes > 1){
       printf("NUMBER OF TRUCKS: \t%i\n", cnrp->numroutes);
       printf("TIGHTNESS: \t\t%.2f\n",
	      cnrp->demand[0]/(cnrp->capacity*(double)cnrp->numroutes));
     }
     
     /* Select the cheapest edges adjacent to each node for the base set */
     if (cnrp->par.use_small_graph == SAVE_SMALL_GRAPH){
       if (!cnrp->g) make_small_graph(cnrp, 0);
       save_small_graph(cnrp);
     }else if (!cnrp->g){
       make_small_graph(cnrp, 0);
     }
     
     /* Check the a priori upper bound and set it if needed */
     sym_get_primal_bound(env, &ub);
     
     printf("ub is: %f", ub);
     if (ub < SYM_INFINITY){
       cnrp->cur_tour->cost = (int) ub;
     }else{
       cnrp->cur_tour->cost = MAXINT;
     }
     cnrp->cur_tour->numroutes = cnrp->numroutes;
     
     if (cnrp->par.use_small_graph == LOAD_SMALL_GRAPH){
       if (ub == SYM_INFINITY && cnrp->cur_tour->cost > 0){
	 ub = sym_set_primal_bound(env, cnrp->cur_tour->cost);
       }
       cnrp->numroutes = cnrp->cur_tour->numroutes;
     }
     
#if 0
     if(cnrp->par.prob_type == BPP)
       sym_set_primal_bound(env, 1);
#endif
     
     if (ub < SYM_INFINITY && !(cnrp->par.prob_type == BPP)){
       printf("INITIAL UPPER BOUND: \t%i\n\n", (int)(ub));
     }else if (!(cnrp->par.prob_type == BPP)){
       printf("INITIAL UPPER BOUND: \tNone\n\n");
     }else{
       printf("\n\n");
     }
     
     /* Create the variable set and decide which variables are in the base set */
     cnrp_create_variables(cnrp);
     
     /* Construct the problem instance and load it into SYMPHONY */
     cnrp_load_problem(env, cnrp);
     
     /* Solve the problem */ 
     
#ifdef MULTI_CRITERIA
     sym_mc_solve(env);
#else
     sym_solve(env);
#endif
   } 

   /* Close the SYMPHONY environment */
   sym_close_environment(env);
   
   return(0);
}

/*===========================================================================*\
 * This is the function that creates the formulation
\*===========================================================================*/

void cnrp_load_problem(sym_environment *env, cnrp_problem *cnrp)
{
   int n, m, nz;
   char *is_int, *sense;
   int *matbeg, *matind;
   double *matval, *obj, *obj2, *rhs, *rngval;
   double *lb, *ub; 
   int *costs = cnrp->dist.cost;
   int i, j;
   char resize = FALSE;
   int vertnum = cnrp->vertnum;
   int total_edgenum = vertnum*(vertnum-1)/2;
   char prob_type = cnrp->par.prob_type;
   int v0, v1;
   double flow_capacity;
   int *edges;
   int *vars, phase, varindex;
#ifdef DIRECTED_X_VARS
   /*whether or not we will have the out-degree constraints*/
   char od_const = (cnrp->par.prob_type == TSP || cnrp->par.prob_type == VRP ||
		    cnrp->par.prob_type == BPP);
   char d_x_vars = TRUE;
#else
   char od_const = FALSE;
   char d_x_vars = FALSE;
#endif
   int varnum = cnrp->basevarnum + cnrp->extravarnum;

#if 0
   if (varnum != 4*total_edgenum){
      printf("Error: Variables missing from problem description.\n");
      printf("Exiting...\n");
      exit(0);
   }
#endif
   
#if defined(ADD_FLOW_VARS)
#ifdef DIRECTED_X_VARS
   flow_capacity = cnrp->capacity;
#else
   if (cnrp->par.prob_type == CSTP || cnrp->par.prob_type == CTP)
      flow_capacity = cnrp->capacity;
   else
      flow_capacity = cnrp->capacity/2;
#endif
#endif

#ifdef MULTI_CRITERIA
   cnrp->lp_par.tau = cnrp->lp_par.gamma = 1.0;
#endif
   
   /* set up the inital LP data */

   n = varnum;
   m = cnrp->basecutnum;
   edges = cnrp->edges;
   
   /*Estimate the number of nonzeros*/
#ifdef ADD_CAP_CUTS
   nz = 12*varnum;
#elif defined(ADD_FLOW_VARS)
   nz = 8*varnum;
#else
   nz = 3*varnum;
#endif
#ifdef ADD_X_CUTS
   nz += 2*varnum;
#endif

   /* Allocate the arrays. These are owned by SYMPHONY after returning. */
   matbeg  = (int *) malloc((n + 1) * ISIZE);
   matind  = (int *) malloc(nz * ISIZE);
   matval  = (double *) malloc(nz * DSIZE);
   obj     = (double *) calloc(n, DSIZE);
   obj2    = (double *) calloc(n, DSIZE);
   ub      = (double *) malloc(n * DSIZE);
   lb      = (double *) calloc(n, DSIZE); /* zero lower bounds */
   rhs     = (double *) malloc(m * DSIZE);
   sense   = (char *) malloc(m * CSIZE);
   rngval  = (double *) calloc(m, DSIZE);
   is_int  = (char *) calloc(n, CSIZE);

   for (i = 0, j = 0; i < varnum; i++){
      if (i < total_edgenum){
	 is_int[i] = TRUE;
	 ub[i] = 1.0;
	 matbeg[i] = j;
	 obj[i] = (double) (cnrp->lp_par.gamma*costs[i]);
	 if (prob_type == CSTP || prob_type == CTP){
	    /*cardinality constraint*/
	    matind[j] = 0;
	    matval[j++] = 1.0;
	 }
	 /*in-degree constraint*/
	 matval[j] = 1.0;
	 matind[j++] = edges[2*i+1];
#ifdef DIRECTED_X_VARS
	 /*out-degree constraint*/
	 if (od_const){
	    matval[j]   = 1.0;
	    matind[j++] = vertnum + edges[2*i];
	 }
#else
	 if (prob_type == VRP || prob_type == TSP ||
	     prob_type == BPP || edges[2*vars[varindex]]){
	    matval[j] = 1.0;
	    matind[j++] = edges[2*i];
	 }
#endif	 
#ifdef ADD_CAP_CUTS
	 v0 = edges[2*i];
	 matval[j] = -flow_capacity + (v0 ? cnrp->demand[v0] : 0);
	 matind[j++] = (2 + od_const)*vertnum - 1 + i;
#ifndef DIRECTED_X_VARS
	 matval[j] = -flow_capacity+cnrp->demand[edges[2*i+1]];
	 matind[j++] = 2*cnrp->vertnum - 1 + total_edgenum + i;
#endif
#endif
#ifdef ADD_X_CUTS
	 matval[j] = 1.0;
	 matind[j++]=(2+od_const)*vertnum-1+2*total_edgenum+i;
#endif
      }
#ifdef DIRECTED_X_VARS
      else if (i < 2*total_edgenum){
	 is_int[i] = TRUE;
	 ub[i] = 1.0;
	 matbeg[i] = j;
	 obj[i] = (double)(cnrp->lp_par.gamma*
			   costs[i-total_edgenum]);
	 if (prob_type == CSTP || prob_type == CTP){
	    /*cardinality constraint*/
	    matind[j] = 0;
	    matval[j++] = 1.0;
	 }
	 /*in-degree constraint*/
	 if (od_const || edges[2*(i - total_edgenum)]){
	    matval[j] = 1.0;
	    matind[j++] = edges[2*(i - total_edgenum)];
	 }
	 /*out-degree constraint*/
	 if (od_const){
	    matval[j] = 1.0;
	    matind[j++] = vertnum+edges[2*(i-total_edgenum)+1];
	 }
#ifdef ADD_CAP_CUTS
	 matval[j] = -flow_capacity +
	    cnrp->demand[edges[2*(i - total_edgenum) + 1]];
	 matind[j++] = (2 + od_const)*vertnum - 1 + i;
#endif
#ifdef ADD_X_CUTS
	 matval[j] = 1.0;
	 matind[j++] = (2 + od_const)* vertnum - 1 + 2 * total_edgenum +
	    i - total_edgenum;
#endif
      }
#endif
      else if (i < (2+d_x_vars)*total_edgenum){
	 is_int[i] = FALSE;
	 v0 = edges[2*(i-(1+d_x_vars)*total_edgenum)];
	 ub[i] = flow_capacity - (v0 ? cnrp->demand[v0] : 0);
	 matbeg[i] = j;
	 obj2[i] = (double)(cnrp->lp_par.tau*
			    costs[i-(1+d_x_vars)*total_edgenum]);
#ifdef ADD_CAP_CUTS
	 matval[j] = 1.0;
	 matval[j+1] = 1.0;
	 if (edges[2*(i-(1+d_x_vars)*total_edgenum)])
	    matval[j+2] = -1.0;
	 matind[j++] = (2 + od_const)*vertnum - 1 + i -
	    (1+d_x_vars)*total_edgenum;
	 matind[j++] = (1+od_const)*vertnum + edges[2*(i -
			       (1+d_x_vars)*total_edgenum) + 1] - 1;
	 if (edges[2*(i - (1+d_x_vars)*total_edgenum)])
	    matind[j++] = (1+od_const)*vertnum + edges[2*(i -
				  (1+d_x_vars)*total_edgenum)] - 1;
#else
	 matval[j] = 1.0;
	 if (edges[2*(i-(1+d_x_vars)*total_edgenum)])
	    matval[j+1] = -1.0;
	 matind[j++] = (1+od_const)*vertnum + edges[2*(i -
			       (1+d_x_vars)*total_edgenum) + 1] - 1;
	 if (edges[2*(i - (1+d_x_vars)*total_edgenum)])
	    matind[j++] = (1+od_const)*vertnum + edges[2*(i -
				  (1+d_x_vars)*total_edgenum)] - 1;
#endif
      }
      else{
	 is_int[i] = FALSE;
	 v1 = edges[2*(i - (2+d_x_vars)*total_edgenum) + 1];
	 ub[i] = flow_capacity - cnrp->demand[v1];
	 matbeg[i] = j;
	 obj2[i] = (double) (cnrp->lp_par.tau*costs[i-
			    (2+d_x_vars)*total_edgenum]);
#ifdef ADD_CAP_CUTS
	 matval[j] = 1.0;
	 matval[j+1] = -1.0;
	 if (edges[2*(i - (2+d_x_vars)*total_edgenum)])
	    matval[j+2] = 1.0;
	 matind[j++] = (2+od_const)*vertnum - 1 + i -
	    (1+d_x_vars)*total_edgenum;
	 matind[j++] = (1+od_const)*vertnum + edges[2*(i -
			       (2+d_x_vars)*total_edgenum)+1] - 1;
	 if (edges[2*(i - (2+d_x_vars)*total_edgenum)])
	    matind[j++] = (1+od_const)*vertnum + edges[2*(i -
				  (2+d_x_vars)*total_edgenum)] - 1;
#else
	 matval[j] = -1.0;
	 if (edges[2*(i - (2+d_x_vars)*total_edgenum)])
	    matval[j+1] = 1.0;
	 matind[j++] = (1+od_const)*vertnum + edges[2*(i -
			       (2+d_x_vars)*total_edgenum)+1] - 1;
	 if (edges[2*(i - (2+d_x_vars)*total_edgenum)])
	    matind[j++] = (1+od_const)*vertnum + edges[2*(i -
				  (2+d_x_vars)*total_edgenum)] - 1;
#endif
      }
   }
   matbeg[i] = j;
   
   /* set the initial right hand side */
   if (od_const){
      /*degree constraints for the depot*/
#if 0
      rhs[0] = cnrp->numroutes;
      sense[0] = 'E';
      rhs[vertnum] = cnrp->numroutes;
      sense[vertnum] = 'E';
#else
      rhs[0] = 1.0;
      sense[0] = 'G';
      rhs[vertnum] = 1.0;
      sense[vertnum] = 'G';
#endif      
   }else if (prob_type == VRP || prob_type == TSP || prob_type == BPP){
      (rhs[0]) = 2*cnrp->numroutes;
      sense[0] = 'E';
   }else{
      /*cardinality constraint*/
      rhs[0] = vertnum - 1;
      sense[0] = 'E';
   }
   for (i = vertnum - 1; i > 0; i--){
      switch (prob_type){
       case VRP:
       case TSP:
       case BPP:
	 if (od_const){
	    rhs[i] = 1.0;
	    sense[i] = 'E';
	    rhs[i+vertnum] = 1.0;
	    sense[i+vertnum] = 'E';
	 }else{
	    rhs[i] = 2.0;
	    sense[i] = 'E';
	 }
	 break;
       case CSTP:
       case CTP:
	 rhs[i] = 1.0;
#ifdef DIRECTED_X_VARS
	 sense[i] = 'E';
#else
	 sense[i] = 'G';
#endif
	 break;
      }
#ifdef ADD_FLOW_VARS
      rhs[(1+od_const)*vertnum + i - 1] = cnrp->demand[i];
      sense[(1+od_const)*vertnum + i - 1] = 'E';
#endif
   }
#ifdef ADD_CAP_CUTS
   for (i = (2+od_const)*vertnum - 1;
	i < (2+od_const)*vertnum - 1 + 2*total_edgenum; i++){
      rhs[i] = 0.0;
      sense[i] = 'L';
   }
#endif
#ifdef ADD_X_CUTS
   for (i = (2+od_const)*vertnum-1+2*total_edgenum;
	i < (2+od_const)*vertnum-1+3*total_edgenum; i++){
      rhs[i] = 1;
      sense[i] = 'L';
   }
#endif
   
   /* Load in the problem */
#ifdef MULTI_CRITERIA
   sym_explicit_load_problem(env, n, m, matbeg, matind, matval, lb, ub, is_int,
			     obj, obj2, sense, rhs, NULL, TRUE);
#else
   sym_explicit_load_problem(env, n, m, matbeg, matind, matval, lb, ub, is_int,
			     obj, obj2, sense, rhs, NULL, FALSE);
#endif   
}      

/*===========================================================================*\
\*===========================================================================*/

int cnrp_test(sym_environment *env)
{

   int termcode, i, file_num = 34;
   char input_files[34][MAX_FILE_NAME_LENGTH +1] = {"A/A-n34-k5.vrp",
						   "A/A-n32-k5.vrp",
						   "A/A-n33-k5.vrp",
						   "E/E-n13-k4.vrp",
						   "E/E-n22-k4.vrp",
						   "E/E-n23-k3.vrp",
						   "E/E-n30-k3.vrp",
						   "E/E-n33-k4.vrp",
						   "V/att-n48-k4.vrp",
						   "E/E-n51-k5.vrp",
						   "A/A-n33-k6.vrp",
						   "A/A-n36-k5.vrp",
						   "A/A-n37-k5.vrp",
						   "A/A-n38-k5.vrp",
						   "A/A-n39-k5.vrp",
						   "A/A-n39-k6.vrp",
						   "A/A-n45-k6.vrp",
						   "A/A-n46-k7.vrp",
						   "B/B-n31-k5.vrp",
						   "B/B-n34-k5.vrp",
						   "B/B-n35-k5.vrp",
						   "B/B-n38-k6.vrp",
						   "B/B-n39-k5.vrp",
						   "B/B-n41-k6.vrp",
						   "B/B-n43-k6.vrp",
						   "B/B-n44-k7.vrp",
						   "B/B-n45-k5.vrp",
						   "B/B-n50-k7.vrp",
						   "B/B-n51-k7.vrp",
						   "B/B-n52-k7.vrp",
						   "B/B-n56-k7.vrp",
						   "B/B-n64-k9.vrp",
						   "A/A-n48-k7.vrp",
						   "A/A-n53-k7.vrp"};   

   double sol[34] = {403, 403, 403,403, 403, 403, 403, 403, 403, 403, 403,
		     403, 403, 403, 403, 403, 403, 403, 403, 403, 403,
		     403, 403, 403, 403, 403, 403, 403, 403, 403, 403,
		     403, 403, 403};
   
   char *input_dir = (char*)malloc(CSIZE*(MAX_FILE_NAME_LENGTH+1));
   char *infile = (char*)malloc(CSIZE*(MAX_FILE_NAME_LENGTH+1));
   double *obj_val = (double *)calloc(DSIZE,file_num);
   double tol = 1e-06, ub;
   cnrp_problem *cnrp = (cnrp_problem *) env->user;
 
   if (strcmp(cnrp->par.test_dir, "") == 0){ 
     strcpy(input_dir, "../../../VRPLIB");
   } else{
     strcpy(input_dir, cnrp->par.test_dir);
   }
  
   sym_set_int_param(env, "verbosity", -10);

   for(i = 0; i<file_num; i++){

     strcpy(infile, "");
     sprintf(infile, "%s%s%s", input_dir, "/", input_files[i]);
     
     cnrp_io(cnrp, infile);
     
     if (!cnrp->g){
       make_small_graph(cnrp, 0);
     }
     sym_get_primal_bound(env, &ub);
     
     if (ub < SYM_INFINITY){
       cnrp->cur_tour->cost = (int) ub;
     }else{
       cnrp->cur_tour->cost = MAXINT;
     }
     cnrp->cur_tour->numroutes = cnrp->numroutes;
     
     cnrp_create_variables(cnrp);
     
     cnrp_load_problem(env, cnrp);
     
     printf("Solving %s...\n", input_files[i]); 
     
     sym_solve(env);
     
     sym_get_obj_val(env, &obj_val[i]);
     
     if((obj_val[i] < sol[i] + tol) && 
	(obj_val[i] > sol[i] - tol)){
       printf("Success!\n");
     } else {
       printf("Failure!(%f, %f) \n", obj_val[i], sol[i]);
     }
     
     if(env->mip->n && i + 1 < file_num ){
       free_master_u(env);
       strcpy(env->par.infile, "");
       
       env->mip = (MIPdesc *) calloc(1, sizeof(MIPdesc));
       cnrp_problem *cnrp = (cnrp_problem *) calloc(1, sizeof(cnrp_problem));
       env->user = (void *) cnrp;
       cnrp_readparams(cnrp, NULL, 0, NULL);
       cnrp->par.prob_type = cnrp->cg_par.prob_type = 
	 cnrp->lp_par.prob_type = CTP;
       cnrp->par.base_variable_selection = SOME_ARE_BASE;
     }
   }
   
   FREE(input_dir);
   FREE(infile);
   FREE(obj_val);
   
   return (0);  
}

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
#include <string.h>

/* SYMPHONY include files */
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#include "sym_master.h"
/*___END_EXPERIMENTAL_SECTION___*/
#include "sym_macros.h"
#include "sym_constants.h"
#include "sym_proccomm.h"
#include "sym_dg_params.h"
#include "sym_master_u.h"

/* CNRP include files */
#include "cnrp_const.h"
#include "cnrp_types.h"
#include "cnrp_io.h"
#include "compute_cost.h"
#include "cnrp_master_functions.h"
#include "cnrp_dg_functions.h"
#include "cnrp_macros.h"
#include "small_graph.h"
#include "network.h"
#ifdef COMPILE_IN_TM
#ifdef COMPILE_IN_LP
#include "cnrp_lp.h"
#ifdef COMPILE_IN_CG
#include "cnrp_cg.h"
#endif
#ifdef COMPILE_IN_CP
#include "cnrp_cp.h"
#endif
#endif
#endif

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions for the master process.
\*===========================================================================*/

void user_usage(void){
         printf("master [ -HEP ] [ -S file ] [ -F file ] [ -B rule ]\n"
		"[ -V sel ] [ -K closest ] [ -N routes ] [ -C capacity ]\n"
		"[ -D level ] [ -M ] [ -X toggle ] [ -Y toggle ] \n"
		"[ -Z toggle ] [-G tau] \n"
		"\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n"
		"\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\n",
		"-H: help",
		"-E: use sparse edge set",
		"-D level: verbosity level for displaying LP solutions",
		"-P type: specify problem type",
		"-S file: load sparse graph from 'file'",
		"-F file: problem data is in 'file'",
		"-B i: which candidates to check in strong branching",
		"-V i: how to construct the base set of variables",
		"-K k: use 'k' closest edges to build sparse graph",
		"-N n: use 'n' routes",
		"-M  : use min cut subroutine",
		"-C c: use capacity 'c'",
		"-X t: toggles generation of X cuts",
		"-Y t: toggles generation of capacity cuts",
		"-Z t: toggles generation of tight capacity cuts",
		"-G t: set tau to 't'");
}

/*===========================================================================*\
 * Initialize user-defined data structures. In this case, I store all
 * problem-specific data such as the location of the customers, edge costs,
 * etc. in this data-structure.
\*===========================================================================*/

int user_initialize(void **user)
{
   cnrp_problem *cnrp = (cnrp_problem *) calloc(1, sizeof(cnrp_problem));

   *user = cnrp;

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * In this function, I set up the user parameters. The first step is to cast
 * the void pointer in order to access my data. In the readparams() function,
 * I read in parameters from the parameter file given on the command line.
\*===========================================================================*/

int user_readparams(void *user, char *filename, int argc, char **argv)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
   p->par.lp_par.problem_type = INTEGER_PROBLEM;
   strcpy(p->par.dg_par.source_path, "/home/tkr/BlackBox/DrawGraph/IGD_1.0/");
#endif
   /*___END_EXPERIMENTAL_SECTION___*/

   cnrp_readparams(cnrp, filename, argc, argv);

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * After I've read in the parameters, I can now read in the data file, whose
 * name was given in the parameter file. This file contains instance data.
\*===========================================================================*/

int user_io(void *user)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;

   cnrp_io(cnrp, cnrp->par.infile);

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
   
   /* Selects the cheapest edges adjacent to each node for the base set */

   if (cnrp->par.use_small_graph == SAVE_SMALL_GRAPH){
      if (!cnrp->g) make_small_graph(cnrp, 0);
      save_small_graph(cnrp);
   }else if (!cnrp->g){
      make_small_graph(cnrp, 0);
   }

   return(USER_SUCCESS);
}
   
/*===========================================================================*/

/*===========================================================================*\
 * Here is where the heuristics are performed and an upper bound is calculated.
 * An upper bound can also be specified in the parameter file. The
 * other thing I do in this routine is build up a graph of the
 * cheapest k edges adjacent to the each node plus any edges chosen
 * during the heuristics to comprise my base set later.
\*===========================================================================*/

int user_start_heurs(void *user, double *ub, double *ub_estimate)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;

   if (*ub > 0){
      cnrp->cur_tour->cost = (int) (*ub);
   }else{
      cnrp->cur_tour->cost = MAXINT;
   }

   cnrp->cur_tour->numroutes = cnrp->numroutes;
   
   if (cnrp->par.use_small_graph == LOAD_SMALL_GRAPH){
      if (*ub <= 0 && cnrp->cur_tour->cost > 0)
	 *ub = (int)(cnrp->cur_tour->cost);
      cnrp->numroutes = cnrp->cur_tour->numroutes;
   }

#if 0
   if(cnrp->par.prob_tpye == BPP)
      *ub = 1;
#endif
   
   if (*ub > 0 && !(cnrp->par.prob_type == BPP))
      printf("INITIAL UPPER BOUND: \t%i\n\n", (int)(*ub));
   else if (!(cnrp->par.prob_type == BPP))
      printf("INITIAL UPPER BOUND: \tNone\n\n");
   else
      printf("\n\n");
   
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * If graph drawing will be use, the user must initialize the drawing
 * window here.
\*===========================================================================*/

int user_init_draw_graph(void *user, int dg_id)
{
#ifndef WIN32   /* FIXME : None of this works in Windows */
   cnrp_problem *cnrp = (cnrp_problem *)user;
   int s_bufid;
      
   if (!(cnrp->posx && cnrp->posy)) return(USER_SUCCESS);
   if ( (cnrp->dg_id = dg_id) ){
      int i, zero = 0, eight = 0x08;
      char node_place[MAX_NAME_LENGTH] = {"node_placement"};
      char weight[5];
      int *posx = cnrp->posx, *posy = cnrp->posy;
      int minx=MAXINT, miny=MAXINT, maxx=-MAXINT, maxy=-MAXINT, xx, yy;
      int width = 1000, height = 700;
#if 0
      int width=p->par.dg_par.canvas_width, height=p->par.dg_par.canvas_height;
#endif
      double mult;

      for (i = cnrp->vertnum - 1; i >= 0; i--){
	 if (posx[i] < minx) minx = posx[i];
	 if (posx[i] > maxx) maxx = posx[i];
	 if (posy[i] < miny) miny = posy[i];
	 if (posy[i] > maxy) maxy = posy[i];
      }
      xx = maxx - minx;
      yy = maxy - miny;
      mult = (int) MIN((width - 20.0)/xx, (height-20.0)/yy);
      width = (int) (xx * mult + 30);
      height = (int) (yy * mult + 30);
      for (i = cnrp->vertnum-1; i >= 0; i--){
	 posx[i] = (int) ((posx[i] - minx) * mult + 10);
	 posy[i] = (int) ((maxy - posy[i]) * mult + 10);
      }

      init_window(dg_id, node_place, width, height);
      /* Now pack the placement of the nodes of the graph */
      s_bufid = init_send(DataInPlace);
      send_str(node_place);
      send_int_array(&cnrp->vertnum, 1);
      for (i = 0; i < cnrp->vertnum; i++){
	 send_int_array(&i, 1);
	 send_int_array(posx + i, 1);
	 send_int_array(posy + i, 1);
	 send_int_array(&eight, 1);
	 sprintf(weight, "%i", (int)(cnrp->demand[i]));
	 send_str(weight);
      }
      /* No edges are passed to the default graph */
      send_int_array(&zero, 1);
      send_msg(dg_id, CTOI_SET_GRAPH);
      freebuf(s_bufid);
      
      display_graph(dg_id, node_place);
   }
#endif

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * In this routine, I build the initial edge set for the root. There are
 * several things going on here. First, there is a user-defined parameter
 * defining whether or not to just go ahead and add all variables to the
 * problem up front (cnrp->par.add_all_edges). Currently, this seems to be the
 * best option since the problems are small anyway. Further, I am doing some
 * preprocessing here by eliminating edges for which the sum of the demands of
 * their endpoints is greater than the capacity since these edges cannot
 * be in any feasible solution.
 *
 * Notice that there are several options programmed for which set
 * of edges should be in the base set. The
 * base constraints are just the degree constraints from the IP
 * formulation. These do not have to be specified explicitly, just the
 * number of them given.
\*===========================================================================*/

int user_initialize_root_node(void *user, int *basevarnum, int **basevars,
			      int *basecutnum, int *extravarnum,
			      int **extravars, char *obj_sense,
			      double *obj_offset, char ***colnames,
			      int *colgen_strat)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;

   *basevarnum = cnrp->basevarnum;
   *basevars = cnrp->basevars;
   *extravarnum = cnrp->extravarnum;
   *extravars = cnrp->extravars;
   *basecutnum = cnrp->basecutnum;

   if (!cnrp->par.colgen_strat[0]){
      if (cnrp->par.add_all_edges ||
	  cnrp->par.base_variable_selection == SOME_ARE_BASE){
	 colgen_strat[0]=(FATHOM__DO_NOT_GENERATE_COLS__DISCARD |
			  BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
      }else{
	 colgen_strat[0] = (FATHOM__DO_NOT_GENERATE_COLS__SEND  |
			    BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
      }
   }else{
      colgen_strat[0] = cnrp->par.colgen_strat[0];
   }
   if (!cnrp->par.colgen_strat[1]){
      if (cnrp->par.add_all_edges ||
	  cnrp->par.base_variable_selection == SOME_ARE_BASE){
	 colgen_strat[1]=(FATHOM__DO_NOT_GENERATE_COLS__DISCARD |
			  BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
      }else{
	 colgen_strat[1] = (FATHOM__GENERATE_COLS__RESOLVE  |
			    BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
      }
   }else{
      colgen_strat[1] = cnrp->par.colgen_strat[1];
   }
   
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

int user_receive_feasible_solution(void *user, int msgtag, double cost,
				   int numvars, int *indices, double *values)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;

   if (cnrp->par.prob_type == TSP || cnrp->par.prob_type == VRP ||
       cnrp->par.prob_type == BPP)
      receive_char_array((char *)cnrp->cur_tour->tour,
			 cnrp->vertnum*sizeof(_node));
   else
      receive_int_array(cnrp->cur_sol_tree, cnrp->vertnum);

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we send the necessary data to the LP process. Notice that
 * there are two cases to deal with. If the LP or the TM are running
 * as separate processes, then we have to send the data by
 * message-passing. Otherwise, we can allocate the user-defined LP data
 * structure here and simply copy the necessary information. This is the
 * only place the user has to sorry about this distinction between
 * configurations. 
\*===========================================================================*/

int user_send_lp_data(void *user, void **user_lp)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP)
   /* This is the case when we are copying data directly because
      the LP is not running separately. This code should be virtually
      identical to that of user_receive_lp_data() in the LP process.*/
   
   cnrp_spec *cnrp_lp = (cnrp_spec *) calloc(1, sizeof(cnrp_spec));
   int zero_varnum = cnrp->zero_varnum;
   int *zero_vars = cnrp->zero_vars;
   int vertnum, i, j, k, l;

   *user_lp = (void *)cnrp_lp;
   
   cnrp_lp->par = cnrp->lp_par;
   cnrp_lp->window = cnrp->dg_id;
   cnrp_lp->numroutes = cnrp->numroutes;
   vertnum = cnrp_lp->vertnum = cnrp->vertnum;
   cnrp_lp->edges = cnrp->edges;
   cnrp_lp->demand = cnrp->demand;
   cnrp_lp->capacity = cnrp->capacity;
   cnrp_lp->costs = cnrp->dist.cost;
   cnrp_lp->utopia_fixed = cnrp->utopia_fixed;
   cnrp_lp->utopia_variable = cnrp->utopia_variable;
   cnrp_lp->variable_cost = cnrp_lp->fixed_cost = MAXDOUBLE;
   cnrp_lp->ub = cnrp->ub;

   if (cnrp->par.prob_type == VRP || cnrp->par.prob_type == TSP ||
       cnrp->par.prob_type == BPP){
      cnrp_lp->cur_sol = (_node *) calloc (cnrp->vertnum, sizeof(_node));
   }else{
      cnrp_lp->cur_sol_tree = (int *) calloc (cnrp->vertnum - 1, ISIZE);
   }
/*__BEGIN_EXPERIMENTAL_SECTION__*/
   if (cnrp_lp->window){
      copy_node_set(cnrp_lp->window, TRUE, (char *)"Weighted solution");
      copy_node_set(cnrp_lp->window, TRUE, (char *)"Flow solution");
   }
/*___END_EXPERIMENTAL_SECTION___*/
   
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_lp_data() in the LP process */
   
   send_char_array((char *)(&cnrp->lp_par), sizeof(cnrp_lp_params));
   send_int_array(&cnrp->dg_id, 1);
   send_int_array(&cnrp->numroutes, 1);
   send_int_array(&cnrp->vertnum, 1);
   send_dbl_array(cnrp->demand, cnrp->vertnum);
   send_dbl_array(&cnrp->capacity, 1);
   send_int_array(cnrp->dist.cost, cnrp->edgenum);
   send_int_array(&cnrp->zero_varnum, 1);
   if (cnrp->zero_varnum){
      send_int_array(cnrp->zero_vars, cnrp->zero_varnum);
   }
   send_dbl_array(&cnrp->utopia_fixed, 1);
   send_dbl_array(&cnrp->utopia_variable, 1);
   send_dbl_array(&cnrp->ub, 1);
#endif

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we send the necessary data to the CG process. Notice that
 * there are two cases to deal with. If the CG, LP, or the TM are running
 * as separate processes, then we have to send the data by
 * message-passing. Otherwise, we can allocate the user-defined LP data
 * structure here and simply copy the necessary information. This is the
 * only place the user has to sorry about this distinction between
 * configurations. 
\*===========================================================================*/

int user_send_cg_data(void *user, void **user_cg)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP) && defined (COMPILE_IN_CG)
   /* This is is the case when we are copying data directly because
      the CG is not running separately. This code should be virtually
      identical to that of user_receive_cg_data() in the CG process.*/
   
   cg_cnrp_spec *cnrp_cg = (cg_cnrp_spec *) malloc (sizeof(cg_cnrp_spec));
   int edgenum, vertnum, i, j, k;
   
   *user_cg = (void *)cnrp_cg;

   cnrp_cg->par = cnrp->cg_par;
   cnrp_cg->numroutes = cnrp->numroutes;
   vertnum = cnrp_cg->vertnum = cnrp->vertnum;
   cnrp_cg->demand = cnrp->demand;
   cnrp_cg->capacity = cnrp->capacity;
   cnrp_cg->dg_id = cnrp->dg_id;
   
   edgenum = cnrp->vertnum*(cnrp->vertnum-1)/2;
      
   cnrp_cg->in_set = (char *) calloc(cnrp->vertnum, sizeof(char));
   cnrp_cg->ref = (int *) malloc(cnrp->vertnum*sizeof(int));
   cnrp_cg->new_demand = (double *) malloc(cnrp->vertnum*sizeof(double));
   cnrp_cg->cut_val = (double *) calloc(cnrp->vertnum, sizeof(double));
   cnrp_cg->cut_list = (char *) malloc(((cnrp->vertnum >> DELETE_POWER)+1)*
				   (cnrp->cg_par.max_num_cuts_in_shrink + 1)*
				   sizeof(char));

   cnrp_cg->edges = (int *) calloc (2*edgenum, sizeof(int));
   
   /*create the edge list (we assume a complete graph)*/
   for (i = 1, k = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
	 cnrp_cg->edges[2*k] = j;
	 cnrp_cg->edges[2*k+1] = i;
	 k++;
      }
   }

#ifdef CHECK_CUT_VALIDITY
   if ((cnrp_cg->feas_sol_size = cnrp->feas_sol_size)){
      cnrp_cg->feas_sol = cnrp->feas_sol;
   }
#endif
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_cg_data() in the CG process */
   
   send_char_array((char *)&cnrp->cg_par, sizeof(cnrp_cg_params));
   send_int_array(&cnrp->dg_id, 1);
   send_int_array(&cnrp->numroutes, 1);
   send_int_array(&cnrp->vertnum, 1);
   send_dbl_array(cnrp->demand, cnrp->vertnum);
   send_dbl_array(&cnrp->capacity, 1);
#ifdef CHECK_CUT_VALIDITY
   send_int_array(&cnrp->feas_sol_size, 1);
   if (cnrp->feas_sol_size){
      send_int_array(cnrp->feas_sol, cnrp->feas_sol_size);
   }
#endif
#endif

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Here, we send the necessary data to the CP process. Notice that
 * there are two cases to deal with. If the CP, LP, or the TM are running
 * as separate processes, then we have to send the data by
 * message-passing. Otherwise, we can allocate the user-defined LP data
 * structure here and simply copy the necessary information. This is the
 * only place the user has to sorry about this distinction between
 * configurations. 
\*===========================================================================*/

int user_send_cp_data(void *user, void **user_cp)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP) && defined (COMPILE_IN_CP)
   /* This is is the case when we are copying data directly because
      the LP is not running separately. This code should be virtually
      identical to that of user_receive_cp_data() in the CP process.*/
   
   cnrp_spec_cp *cnrp_cp = (cnrp_spec_cp *) malloc (sizeof(cnrp_spec_cp));
   int i, j, k;

   cnrp_cp->par = cnrp->cp_par;
   cnrp_cp->vertnum = cnrp->vertnum;
   cnrp_cp->capacity = cnrp->capacity;
   cnrp_cp->demand = (double *) malloc(cnrp->vertnum * DSIZE);
   memcpy((char *)cnrp_cp->demand, (char *) cnrp->demand, cnrp->vertnum * DSIZE); 

   *user_cp = (void *)cnrp_cp;

   cnrp_cp->edgenum =
      cnrp_cp->vertnum*(cnrp_cp->vertnum-1)/2 + cnrp_cp->vertnum-1;
   cnrp_cp->edges = (int *) calloc ((int)2*cnrp_cp->edgenum, sizeof(int));
     
   /* create the edge list (we assume a complete graph) */
   for (i = 1, k = 0; i < cnrp_cp->vertnum; i++){
      for (j = 0; j < i; j++){
	 cnrp_cp->edges[2*k] = j;
	 cnrp_cp->edges[2*k+1] = i;
	 k++;
      }
   }

   /* now add the duplicate copies of the depot edges to allow for
      routes with one customer */
   for (i = 1; i < cnrp_cp->vertnum; i++){
      cnrp_cp->edges[2*k] = 0;
      cnrp_cp->edges[2*k+1] = i;
      k++;
   }
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_cp_data() in the CP process */
   
   send_int_array(&cnrp->vertnum, 1);
   send_dbl_array(&cnrp->capacity, 1);
   send_dbl_array(cnrp->demand, cnrp->vertnum);
   
#endif

   return(USER_SUCCESS);
}

/*__BEGIN_EXPERIMENTAL_SECTION__*/
/*===========================================================================*/

int user_send_sp_data(void *user)
{
   return(USER_SUCCESS);
}

/*___END_EXPERIMENTAL_SECTION___*/
/*===========================================================================*/

/*===========================================================================*\
 * Generally, this function is not needed but you might find some use
 * for it. Someone did :).
\*===========================================================================*/

int user_process_own_messages(void *user, int msgtag)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * This is the user's chance to display the solution in whatever
 * manner desired. In my case, I can display a text version, which is
 * just a list of the customers on each route, or use the interactive
 * Graph Drawing application to graphically display the solution.
\*===========================================================================*/

int user_display_solution(void *user, double lpetol, int varnum, int *indices,
			  double *values, double objval)
{
   cnrp_problem *cnrp = (cnrp_problem *)user;
   _node *tour = cnrp->cur_tour->tour;
   int *tree = cnrp->cur_sol_tree, node, prev_node;
   int cur_vert = 0, prev_vert = 0, cur_route, i, count;
   elist *cur_route_start = NULL;
   edge *edge_data;
   vertex *verts;
   double fixed_cost = 0.0, variable_cost = 0.0;
   int window = cnrp->dg_id;
   int vertnum = cnrp->vertnum, v0, v1;
   int total_edgenum =  vertnum*(vertnum-1)/2;
   network *n;

   /* FIXME: This is UGLY! */
#if (defined(MULTI_CRITERIA) && defined(FIND_NONDOMINATED_SOLUTIONS)) && \
   (defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP)) && 0
      
   problem *p = get_problem_ptr(FALSE);
   cnrp_spec *cnrp_lp = (cnrp_spec *) p->tm->lpp[0]->user;

   cnrp->fixed_cost = cnrp_lp->fixed_cost;
   cnrp->variable_cost = cnrp_lp->variable_cost;

   tour = cnrp_lp->cur_sol;
   tree = cnrp_lp->cur_sol_tree;
   printf("\nSolution Found:\n");
#ifdef ADD_FLOW_VARS
   printf("Solution Fixed Cost: %.1f\n", cnrp->fixed_cost);
   printf("Solution Variable Cost: %.1f\n", cnrp->variable_cost);
#else
   printf("Solution Cost: %.0f\n", fixed_cost);
#endif
#else
   printf("\nSolution Found:\n");
#endif

#if 0
   if (tour){
      node = tour[0].next;
      if (tour[0].route == 1)
	 printf("\n0 ");
      while (node != 0){
	 if (tour[prev_node].route != tour[node].route){
	    printf("\nRoute #%i: ", tour[node].route);
	    count = 0;
	 }
	 printf("%i ", node);
	 count++;
	 if (count > 15){
	    printf("\n");
	    count = 0;
	 }
	 prev_node = node;
	 node = tour[node].next;
      }
      printf("\n\n");
      
      if (window){
	 char name[MAX_NAME_LENGTH] = {"feas_solution"};
	 disp_vrp_tour(window, TRUE, name, tour, cnrp->vertnum,
			cnrp->numroutes, CTOI_WAIT_FOR_CLICK_AND_REPORT);
      }
      return(USER_SUCCESS);
   }

   if (tree){
      printf("Edge List:\n");
      for (i = 0; i < vertnum - 1; i++){
	 BOTH_ENDS(tree[i], &v0, &v1);
	 printf("%i %i\n", v1, v0);
      }
      printf("\n\n");

      if (window){
	 char name[MAX_NAME_LENGTH] = {"feas_solution"};
	 copy_node_set(window, TRUE, name);
	 draw_edge_set_from_userind(window, name, vertnum - 1, tree);
	 display_graph(window, name);
	 wait_for_click(window, name, CTOI_WAIT_FOR_CLICK_NO_REPORT);
      }
      return(USER_SUCCESS);
   }
#endif
   
   /*Otherwise, construct the solution from scratch*/

#ifdef ADD_FLOW_VARS
   n = create_flow_net(indices, values, varnum, lpetol, cnrp->edges,
		       cnrp->demand, vertnum);
#else
   n = create_net(indices, values, varnum, lpetol, cnrp->edges, cnrp->demand,
		  vertnum);
#endif

   for (i = 0; i < n->edgenum; i++){
      if (n->edges[i].weight > 1 - lpetol){
	 fixed_cost += cnrp->dist.cost[INDEX(n->edges[i].v0, n->edges[i].v1)];
      }
#ifdef ADD_FLOW_VARS
      variable_cost += (n->edges[i].flow1+n->edges[i].flow2)*
	 cnrp->dist.cost[INDEX(n->edges[i].v0, n->edges[i].v1)];
#endif
   }
   cnrp->fixed_cost = fixed_cost;
   cnrp->variable_cost = variable_cost;
#if defined(ADD_FLOW_VARS) && defined(MULTI_CRITERIA)
   printf("Solution Fixed Cost: %.1f\n", fixed_cost);
   printf("Solution Variable Cost: %.1f\n", variable_cost);
#else
   printf("Solution Cost: %.0f\n", fixed_cost);
#endif

   if (cnrp->par.prob_type == TSP || cnrp->par.prob_type == VRP ||
       cnrp->par.prob_type == BPP){ 

      verts = n->verts;
   
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
      printf("\n");
   }else{
      
      for (i = 0; i < n->edgenum; i++){
	 cnrp->cur_sol_tree[i] = INDEX(n->edges[i].v0, n->edges[i].v1);
      }
      
      /* Display the solution */
      
      for (i = 0; i < n->edgenum; i++){
	 printf("%i %i\n", n->edges[i].v0, n->edges[i].v1);
      }
      printf("\n");
   }
   free_net(n);

   return(USER_SUCCESS);
}
   
/*===========================================================================*/

/*===========================================================================*\
 * This is a debugging feature which might
 * allow you to find out why a known feasible solution is being cut off.
\*===========================================================================*/

int user_send_feas_sol(void *user, int *feas_sol_size, int **feas_sol)
{
#ifdef TRACE_PATH
   cnrp_problem *cnrp = (cnrp_problem *)user;

   *feas_sol_size = cnrp->feas_sol_size;
   *feas_sol = cnrp->feas_sol;
#endif
   return(USER_SUCCESS);
}   

/*===========================================================================*/

/*===========================================================================*\
 * This function frees everything.
\*===========================================================================*/

int user_free_master(void **user)
{
   cnrp_problem *cnrp = (cnrp_problem *)(*user);

   if (cnrp->cur_tour){
      FREE(cnrp->cur_tour->tour);
      FREE(cnrp->cur_tour->route_info);
      FREE(cnrp->cur_tour);
   }
   FREE(cnrp->cur_sol_tree);
   FREE(cnrp->posy);
   FREE(cnrp->posx);
   FREE(cnrp->dist.coordx);
   FREE(cnrp->dist.coordy);
   FREE(cnrp->dist.coordz);
   FREE(cnrp->dist.cost);
   FREE(cnrp->edges);
   FREE(cnrp->demand);
   if (cnrp->g){
      FREE(cnrp->g->edges);
      FREE(cnrp->g);
   }
#ifdef CHECK_CUT_VALIDITY
   FREE(cnrp->feas_sol);
#endif
   FREE(cnrp->zero_vars);
   FREE(cnrp);

   return(USER_SUCCESS);
}
/*===========================================================================*/

/*===========================================================================*\
 * This function is used to lift the user created cuts during warm starting *
\*===========================================================================*/

int user_ws_update_cuts (void *user, int *size, char **coef, double * rhs, 
			 char *sense, char type, int new_col_num, 
			 int change_type)
{
   return(USER_DEFAULT);
}

/*===========================================================================*/








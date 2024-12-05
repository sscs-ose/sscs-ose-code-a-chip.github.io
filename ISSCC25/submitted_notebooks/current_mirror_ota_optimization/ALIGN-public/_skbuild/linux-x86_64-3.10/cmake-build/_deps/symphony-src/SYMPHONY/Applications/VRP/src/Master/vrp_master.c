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
#include <math.h>

/* SYMPHONY include files */
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#include "sym_master.h"
/*___END_EXPERIMENTAL_SECTION___*/
#include "sym_macros.h"
#include "sym_constants.h"
#include "sym_proccomm.h"
#include "sym_qsort.h"
#include "sym_dg_params.h"
#include "sym_master_u.h"

/* VRP include files */
#include "vrp_const.h"
#include "vrp_types.h"
#include "vrp_io.h"
#include "compute_cost.h"
#include "network.h"
#ifdef COMPILE_HEURS
#include "start_heurs.h"
#endif
#include "vrp_master_functions.h"
#include "vrp_dg_functions.h"
#include "vrp_macros.h"
#include "small_graph.h"
#ifdef COMPILE_IN_TM
#ifdef COMPILE_IN_CP
#include "vrp_cp.h"
#endif
#ifdef COMPILE_IN_LP
#include "vrp_lp.h"
#ifdef COMPILE_IN_CG
#include "vrp_cg.h"
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef COMPILE_OUR_DECOMP
#include "my_decomp.h"
#endif
/*___END_EXPERIMENTAL_SECTION___*/
#endif
#endif
#endif

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the user-written functions for the master process.
\*===========================================================================*/

void user_usage(void){
   printf("vrp [ -HEPT ] [ -S file ] [ -F file ] [ -B rule ]\n\t"
	  "[ -V sel ] [ -K closest ] [ -N routes ] [ -C capacity ]\n"
	  "\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n\t%s\n"
	  "\t%s\n\t%s\n\t%s\n"
/*__BEGIN_EXPERIMENTAL_SECTION__*/
          "\t%s\n"
/*___END_EXPERIMENTAL_SECTION___*/
          "\n",
	  "-H: help",
	  "-E: use sparse edge set",
	  "-T: solve as a Traveling Salesman Problem",
	  "-S file: load sparse graph from 'file'",
	  "-F file: problem data is in 'file'",
	  "-B i: which candidates to check in strong branching",
	  "-A i: how to construct the base set of variables",
	  "-V i: verbosity level",
	  "-K k: use 'k' closest edges to build sparse graph",
	  "-N n: use 'n' routes",
/*__BEGIN_EXPERIMENTAL_SECTION__*/
	  "-P: solve as a Bin Packing Problem",
/*___END_EXPERIMENTAL_SECTION___*/
	  "-C c: use capacity 'c'");
}

/*===========================================================================*\
 * Initialize user-defined data structures. In this case, I store all
 * problem-specific data such as the location of the customers, edge costs,
 * etc. in this data-structure.
\*===========================================================================*/

int user_initialize(void **user)
{
   vrp_problem *vrp = (vrp_problem *) calloc(1, sizeof(vrp_problem));

   *user = vrp;

   vrp_set_defaults(vrp);
   
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
   vrp_problem *vrp = (vrp_problem *)user;

   vrp_readparams(vrp, filename, argc, argv);

#if 0
   if (vrp->par.use_small_graph == LOAD_SMALL_GRAPH){
      read_small_graph(vrp);
      vrp->numroutes = vrp->cur_tour->numroutes;
   }

   /* Selects the cheapest edges adjacent to each node for the base set */

   if (vrp->par.use_small_graph == SAVE_SMALL_GRAPH){
      if (!vrp->g) make_small_graph(vrp, 0);
      save_small_graph(vrp);
   }else if (!vrp->g){
      make_small_graph(vrp, 0);
   }
#endif
   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * After I've read in the parameters, I can now read in the data file, whose
 * name was given in the parameter file. This file contains instance data.
\*===========================================================================*/

int user_io(void *user)
{
   vrp_problem *vrp = (vrp_problem *)user;
   int i;

   if (strcmp(vrp->par.infile, "")){
      vrp_io(vrp, vrp->par.infile);
   }

   if (vrp->numroutes == 1){
      vrp->par.tsp_prob = TRUE;
      vrp->capacity = vrp->vertnum;
      vrp->numroutes = 1;
      vrp->demand = (int *) malloc (vrp->vertnum * ISIZE);
      vrp->demand[0] = vrp->vertnum;
      for (i = vrp->vertnum - 1; i > 0; i--)
	 vrp->demand[i] = 1;
      vrp->cg_par.tsp_prob = TRUE;
      if (!vrp->cg_par.which_tsp_cuts)
	 vrp->cg_par.which_tsp_cuts = ALL_TSP_CUTS;
   }
   
   vrp->cur_tour = (best_tours *) calloc(1, sizeof(best_tours));
   vrp->cur_tour->tour = (_node *) calloc(vrp->vertnum, sizeof(_node));
#ifdef COMPILE_HEURS
   vrp->tours = (best_tours *) calloc(vrp->par.tours_to_keep,
				      sizeof(best_tours));
#endif
  
   if (vrp->par.k_closest < 0){
      vrp->par.k_closest = (int) (ceil(0.1 * vrp->vertnum));
      if (vrp->par.k_closest < vrp->par.min_closest ) 
	 vrp->par.k_closest = vrp->par.min_closest;
      if (vrp->par.k_closest > vrp->par.max_closest) 
	 vrp->par.k_closest = vrp->par.max_closest;
      if (vrp->par.k_closest > vrp->vertnum-1) 
	 vrp->par.k_closest = vrp->vertnum-1;
   }

   if (vrp->par.use_small_graph == LOAD_SMALL_GRAPH){
      read_small_graph(vrp);
      vrp->numroutes = vrp->cur_tour->numroutes;
   }
  
   /* Selects the cheapest edges adjacent to each node for the base set */
  
   if (vrp->par.use_small_graph == SAVE_SMALL_GRAPH){
      if (!vrp->g) make_small_graph(vrp, 0);
      save_small_graph(vrp);
   }else if (!vrp->g){
      make_small_graph(vrp, 0);
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
   vrp_problem *vrp = (vrp_problem *)user;

   if (*ub > 0){
      vrp->cur_tour->cost = (int) (*ub);
   }else if (vrp->cur_tour->cost > 0){
      *ub = (int)(vrp->cur_tour->cost);
   }else{
      vrp->cur_tour->cost = MAXINT;
   }

   vrp->cur_tour->numroutes = vrp->numroutes;
   
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   if(vrp->par.bpp_prob)
      *ub = 1;
   /*___END_EXPERIMENTAL_SECTION___*/
   
#ifdef COMPILE_HEURS
   if (vrp->par.do_heuristics || vrp->lb_par.lower_bound)
      start_heurs(vrp, &vrp->heur_par, &vrp->lb_par, ub, FALSE);
   else
      vrp->tournum = -1;
#endif
   
   if (!vrp->numroutes){
      printf("\nError: Number of trucks not specified or computed "
	     "for VRP\n\n");
      exit(1);
   }

   if (vrp->par.verbosity < 0){
      return(USER_SUCCESS);
   }
   
   if (vrp->numroutes > 1){
      printf("NUMBER OF TRUCKS: \t%i\n", vrp->numroutes);
      printf("TIGHTNESS: \t\t%.2f\n",
     (double)vrp->demand[0]/((double)vrp->capacity*(double)vrp->numroutes));
   }
   

   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   if (*ub > 0 && !vrp->par.bpp_prob)
      printf("INITIAL UPPER BOUND: \t%i\n\n", (int)(*ub));
   else if (!vrp->par.bpp_prob)
      printf("INITIAL UPPER BOUND: \tNone\n\n");
   else
      printf("\n\n");
   /*___END_EXPERIMENTAL_SECTION___*/
   /*UNCOMMENT FOR PRODUCTION CODE*/
#if 0
   if (*ub > 0)
      printf("INITIAL UPPER BOUND: \t%i\n\n", (int)(*ub));
   else
      printf("INITIAL UPPER BOUND: \tNone\n\n");
#endif
   
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
   vrp_problem *vrp = (vrp_problem *)user;
   int s_bufid;
      
   if (!(vrp->posx && vrp->posy)) return(USER_NO_PP);
   if ( (vrp->dg_id = dg_id) ){
      int i, zero = 0, eight = 0x08;
      char node_place[MAX_NAME_LENGTH] = {"node_placement"};
      char weight[5];
      int *posx = vrp->posx, *posy = vrp->posy;
      int minx=MAXINT, miny=MAXINT, maxx=-MAXINT, maxy=-MAXINT, xx, yy;
      int width = 1000, height = 700;
#if 0
      int width=p->par.dg_par.canvas_width, height=p->par.dg_par.canvas_height;
#endif
      double mult;

      for (i = vrp->vertnum - 1; i >= 0; i--){
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
      for (i = vrp->vertnum-1; i >= 0; i--){
	 posx[i] = (int) ((posx[i] - minx) * mult + 10);
	 posy[i] = (int) ((maxy - posy[i]) * mult + 10);
      }

      init_window(dg_id, node_place, width, height);
      /* Now pack the placement of the nodes of the graph */
      s_bufid = init_send(DataInPlace);
      send_str(node_place);
      send_int_array(&vrp->vertnum, 1);
      for (i = 0; i < vrp->vertnum; i++){
	 send_int_array(&i, 1);
	 send_int_array(posx + i, 1);
	 send_int_array(posy + i, 1);
	 send_int_array(&eight, 1);
	 sprintf(weight, "%i", vrp->demand[i]);
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
 * problem up front (vrp->par.add_all_edges). Currently, this seems to be the
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
   vrp_problem *vrp = (vrp_problem *)user;
   int base_varnum = 0;
   int i, j, k, l;
   int zero_varnum, *zero_vars;
   int vertnum = vrp->vertnum;
   int *edges;

   /* Form the set of base variables */
   switch(vrp->par.base_variable_selection){
    case SOME_ARE_BASE:
      if (vrp->par.add_all_edges == FALSE)
	 /*If we are not adding all the edges, then really EVERYTHING_IS_BASE*/
	 vrp->par.base_variable_selection = EVERYTHING_IS_BASE;
      else /*Otherwise, all we need to do is set this and then fall through --
	     the remaining edges get added in user_create_root()*/
	 vrp->par.add_all_edges = FALSE;


    case EVERYTHING_IS_BASE:
      *basevars = create_edge_list(vrp, &base_varnum, CHEAP_EDGES);
      
      *basevars = (int *) realloc((char *)(*basevars), base_varnum * ISIZE);
      *basevarnum = base_varnum;
      
      break;

    case EVERYTHING_IS_EXTRA:
      *basevarnum = 0;
      break;
   }
   
   *basecutnum = vertnum;

   if (!vrp->par.colgen_strat[0]){
#if 0
      /* Currently, column generation is broken */
      if (vrp->par.add_all_edges ||
	  vrp->par.base_variable_selection == SOME_ARE_BASE){
	 colgen_strat[0]=(FATHOM__DO_NOT_GENERATE_COLS__DISCARD |
			  BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
      }else{
	 colgen_strat[0] = (FATHOM__DO_NOT_GENERATE_COLS__SEND  |
			    BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
      }
#endif
      colgen_strat[0]=(FATHOM__DO_NOT_GENERATE_COLS__DISCARD |
		       BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
   }else{
      colgen_strat[0] = vrp->par.colgen_strat[0];
   }
   if (!vrp->par.colgen_strat[1]){
      if (vrp->par.add_all_edges ||
	  vrp->par.base_variable_selection == SOME_ARE_BASE){
	 colgen_strat[1]=(FATHOM__DO_NOT_GENERATE_COLS__DISCARD |
			  BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
      }else{
	 colgen_strat[1] = (FATHOM__GENERATE_COLS__RESOLVE  |
			    BEFORE_BRANCH__DO_NOT_GENERATE_COLS);
      }
   }else{
      colgen_strat[1] = vrp->par.colgen_strat[1];
   }
   
   /*create the edge list (we assume a complete graph) The edge is set to
     (0,0) in the edge list if it was eliminated in preprocessing*/
   edges = vrp->edges = (int *) calloc (vertnum*(vertnum-1), sizeof(int));
   zero_varnum = vrp->zero_varnum;
   zero_vars = vrp->zero_vars;
   for (i = 1, k = 0, l = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
	 if (l < zero_varnum && k == zero_vars[l]){
	    /*This is one of the zero edges*/
	    edges[2*k] = edges[2*k+1] = 0;
	    l++;
	    k++;
	    continue;
	 }
	 edges[2*k] = j;
	 edges[2*k+1] = i;
	 k++;
      }
   }

/*__BEGIN_EXPERIMENTAL_SECTION__*/
   if (vrp->par.bpp_prob){
      for (i = 0; i < *basevarnum; i++){
	 vrp->dist.cost[(*basevars)[i]] = 10;
      }
   }
/*___END_EXPERIMENTAL_SECTION___*/

   /* Form the set of extra variables */
   switch(vrp->par.base_variable_selection){
    case EVERYTHING_IS_EXTRA:

      *extravars  = create_edge_list(vrp, extravarnum, CHEAP_EDGES);
      
      break;

    case SOME_ARE_BASE:
      
      vrp->par.add_all_edges = TRUE; /*We turned this off in user_set_base()
				       -- now we need to turn it back on*/

      *extravars  = create_edge_list(vrp, extravarnum, REMAINING_EDGES);

      break;

    case EVERYTHING_IS_BASE:

      break;
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
   vrp_problem *vrp = (vrp_problem *)user;

   receive_char_array((char *)vrp->cur_tour->tour, vrp->vertnum*sizeof(_node));

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
   vrp_problem *vrp = (vrp_problem *)user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP)
   /* This is the case when we are copying data directly because
      the LP is not running separately. This code should be virtually
      identical to that of user_receive_lp_data() in the LP process.*/
   
   vrp_lp_problem *vrp_lp = (vrp_lp_problem *) calloc(1,
						      sizeof(vrp_lp_problem));
   *user_lp = (void *)vrp_lp;
   
   vrp_lp->par = vrp->lp_par;
   vrp_lp->window = vrp->dg_id;
   vrp_lp->numroutes = vrp->numroutes;
   vrp_lp->vertnum = vrp->vertnum;
   vrp_lp->edges = vrp->edges;
   vrp_lp->demand = vrp->demand;
   vrp_lp->capacity = vrp->capacity;
   vrp_lp->costs = vrp->dist.cost;

   vrp_lp->cur_sol = (_node *) calloc (vrp_lp->vertnum, sizeof(_node));
/*__BEGIN_EXPERIMENTAL_SECTION__*/

   if (vrp_lp->window){
      copy_node_set(vrp_lp->window, TRUE, (char *)"Original solution");
#if 0
      copy_node_set(vrp_lp->window, TRUE, (char *)"Compressed solution");
#endif
   }

/*___END_EXPERIMENTAL_SECTION___*/
   
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_lp_data() in the LP process */
   
   send_char_array((char *)(&vrp->lp_par), sizeof(vrp_lp_params));
   send_int_array(&vrp->dg_id, 1);
   send_int_array(&vrp->numroutes, 1);
   send_int_array(&vrp->vertnum, 1);
   send_int_array(vrp->demand, vrp->vertnum);
   send_int_array(&vrp->capacity, 1);
   send_int_array(vrp->dist.cost, vrp->edgenum);
   send_int_array(&vrp->zero_varnum, 1);
   if (vrp->zero_varnum){
      send_int_array(vrp->zero_vars, vrp->zero_varnum);
   }
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
   vrp_problem *vrp = (vrp_problem *)user;

#if defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP) && defined (COMPILE_IN_CG)
   /* This is is the case when we are copying data directly because
      the CG is not running separately. This code should be virtually
      identical to that of user_receive_cg_data() in the CG process.*/
   
   vrp_cg_problem *vrp_cg = (vrp_cg_problem *) malloc (sizeof(vrp_cg_problem));
   int edgenum, vertnum, i, j, k;
   
   *user_cg = (void *)vrp_cg;

   vrp_cg->par = vrp->cg_par;
   vrp_cg->numroutes = vrp->numroutes;
   vertnum = vrp_cg->vertnum = vrp->vertnum;
   vrp_cg->demand = (int *) malloc(vrp->vertnum*sizeof(int));
   memcpy(vrp_cg->demand, vrp->demand, vrp->vertnum*sizeof(int));
   vrp_cg->capacity = vrp->capacity;
   vrp_cg->dg_id = vrp->dg_id;
   
   edgenum = vrp->vertnum*(vrp->vertnum-1)/2;
      
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef COMPILE_OUR_DECOMP
   if (vrp->cg_par.do_our_decomp){
      vrp_cg->cost = vrp->dist.cost;
      usr_open_decomp_lp( get_cg_ptr(NULL), edgenum );
   }
   vrp_cg->last_decomp_index = -1;
#endif   
/*___END_EXPERIMENTAL_SECTION___*/
   vrp_cg->in_set = (char *) calloc(vrp->vertnum, sizeof(char));
   vrp_cg->ref = (int *) malloc(vrp->vertnum*sizeof(int));
   vrp_cg->new_demand = (int *) malloc(vrp->vertnum*sizeof(int));
   vrp_cg->cut_val = (double *) calloc(vrp->vertnum, sizeof(double));
   vrp_cg->cut_list = (char *) malloc(((vrp->vertnum >> DELETE_POWER)+1)*
				   (vrp->cg_par.max_num_cuts_in_shrink + 1)*
				   sizeof(char));

   vrp_cg->edges = (int *) calloc (2*edgenum, sizeof(int));
   
   /*create the edge list (we assume a complete graph)*/
   for (i = 1, k = 0; i < vertnum; i++){
      for (j = 0; j < i; j++){
	 vrp_cg->edges[2*k] = j;
	 vrp_cg->edges[2*k+1] = i;
	 k++;
      }
   }

#ifdef CHECK_CUT_VALIDITY
   if ((vrp_cg->feas_sol_size = vrp->feas_sol_size)){
      vrp_cg->feas_sol = vrp->feas_sol;
   }
#endif
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_cg_data() in the CG process */
   
   send_char_array((char *)&vrp->cg_par, sizeof(vrp_cg_params));
   send_int_array(&vrp->dg_id, 1);
   send_int_array(&vrp->numroutes, 1);
   send_int_array(&vrp->vertnum, 1);
   send_int_array(vrp->demand, vrp->vertnum);
   send_int_array(&vrp->capacity, 1);
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   if (vrp->cg_par.do_our_decomp)/* need to send costs to CG too */
      send_int_array(vrp->dist.cost, vrp->edgenum);
   /*___END_EXPERIMENTAL_SECTION___*/
#ifdef CHECK_CUT_VALIDITY
   send_int_array(&vrp->feas_sol_size, 1);
   if (vrp->feas_sol_size){
      send_int_array(vrp->feas_sol, vrp->feas_sol_size);
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
   vrp_problem *vrp = (vrp_problem *)user;

#if defined(COMPILE_IN_TM) && defined (COMPILE_IN_CP)
   /* This is is the case when we are copying data directly because
      the LP is not running separately. This code should be virtually
      identical to that of user_receive_cp_data() in the CP process.*/
   
   vrp_cp_problem *vrp_cp = (vrp_cp_problem *) malloc (sizeof(vrp_cp_problem));
   int i, j, k;

   vrp_cp->vertnum = vrp->vertnum;

   *user_cp = (void *)vrp_cp;

   vrp_cp->edgenum = vrp_cp->vertnum*(vrp_cp->vertnum-1)/2 + vrp_cp->vertnum-1;
   vrp_cp->edges = (int *) calloc ((int)2*vrp_cp->edgenum, sizeof(int));
     
   /* create the edge list (we assume a complete graph) */
   for (i = 1, k = 0; i < vrp_cp->vertnum; i++){
      for (j = 0; j < i; j++){
	 vrp_cp->edges[2*k] = j;
	 vrp_cp->edges[2*k+1] = i;
	 k++;
      }
   }

   /* now add the duplicate copies of the depot edges to allow for
      routes with one customer */
   for (i = 1; i < vrp_cp->vertnum; i++){
      vrp_cp->edges[2*k] = 0;
      vrp_cp->edges[2*k+1] = i;
      k++;
   }
#else
   /* Here, we send that data using message passing and the rest is
      done in user_receive_cp_data() in the CP process */
   
   send_int_array(&vrp->vertnum, 1);
#endif

   return(USER_SUCCESS);
}

/*__BEGIN_EXPERIMENTAL_SECTION__*/
/*===========================================================================*/

int user_send_sp_data(void *user)
{
#ifdef COMPILE_HEURS
   vrp_problem *vrp = (vrp_problem *) user;
   int i, j;
   int size;
   _node *tour;
   int *coef;
   int tournum = vrp->tournum + 1 + vrp->sol_pool_col_num;
   int cur_node, next_node;
   int v0, v1;
   int vertnum = vrp->vertnum;
   /*FIXME: temporary fix to allow this to compile without PVM*/

   coef = (int *) calloc (vrp->vertnum - 1 + vrp->numroutes, ISIZE);
   size = (vrp->vertnum-1 + vrp->numroutes) * ISIZE;
   
   send_int_array(&vrp->vertnum, 1);
   
   send_int_array(&tournum, 1);

   if (tournum <= 0){
      return(USER_SUCCESS);
   }

   for (i = 0; i<=vrp->tournum; i++){
      tour = vrp->tours[i].tour;
      coef[0] = INDEX(0, tour[0].next);
      for (cur_node = tour[0].next, next_node = tour[cur_node].next, j = 1;
	   cur_node;
	   cur_node = next_node, next_node = tour[next_node].next, j++){
	 if(tour[cur_node].route == tour[next_node].route){
	    coef[j] = INDEX(cur_node, next_node);
	 }else if (next_node){
	    coef[j++] = INDEX(0, cur_node);
	    if (coef[j-1] == coef[j-2])
	       coef[j-1] = vertnum*(vertnum-1)/2 + cur_node - 1;
	    coef[j] = INDEX(0, next_node);
	 }else{
	    coef[j] = INDEX(0, cur_node);
	 }
      }

      qsort_i(coef, size/sizeof(int));
      
      send_int_array(&size, 1);
      send_char_array((char *)coef, size);
   }

   for (i = 0; i<vrp->sol_pool_col_num; i++){
      for (j = 0; j < 2*size/sizeof(int); j+=2){
	 v0 = vrp->sol_pool_cols[2*i*size/ISIZE + j];
	 v1 = vrp->sol_pool_cols[2*i*size/ISIZE + j + 1];
	 coef[j/2] = INDEX(v0, v1);
      }
      qsort_i(coef, size/ISIZE);
      
      send_int_array(&size, 1);
      send_char_array((char *)coef, size);
   }
#endif

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
   vrp_problem *vrp = (vrp_problem *)user;
   _node *tour = vrp->cur_tour->tour;
   int window = vrp->dg_id;
   
   int prev_node = 0, node, count = 0;
   
   if (!tour || vrp->cur_tour->cost > (int) objval){ /* Construct the tour */
      int cur_vert = 0, prev_vert = 0, cur_route;
      elist *cur_route_start = NULL;
      edge *edge_data;
      double cost = 0;
      network *n = createnet(indices, values, varnum, lpetol, vrp->edges,
			     vrp->demand, vrp->vertnum);
      vertex *verts = n->verts;

      if (!tour)
	 tour = vrp->cur_tour->tour = (_node *) calloc (vrp->vertnum,
							sizeof(_node));

      for (cur_route_start = verts[0].first, cur_route = 1, cost = 0,
	      edge_data = cur_route_start->data; cur_route <= vrp->numroutes;
	   cur_route++){
	 edge_data = cur_route_start->data;
	 edge_data->scanned = TRUE;
	 cur_vert = edge_data->v1;
	 tour[prev_vert].next = cur_vert;
	 tour[cur_vert].route = cur_route;
	 prev_vert = 0;
	 cost += vrp->dist.cost[INDEX(prev_vert, cur_vert)];
	 while (cur_vert){
	    if (verts[cur_vert].first->other_end != prev_vert){
	       prev_vert = cur_vert;
	       edge_data = verts[cur_vert].first->data;
	       cur_vert = verts[cur_vert].first->other_end;
	    }
	    else{
	       prev_vert = cur_vert;
	       edge_data = verts[cur_vert].last->data; /*This statement could
							 possibly be taken out
							 to speed things up a
							 bit */
	       cur_vert = verts[cur_vert].last->other_end;
	    }
	    tour[prev_vert].next = cur_vert;
	    tour[cur_vert].route = cur_route;
	    cost += vrp->dist.cost[INDEX(prev_vert, cur_vert)];
	 }
	 edge_data->scanned = TRUE;
	 
	 while (cur_route_start->data->scanned){
	    if (!(cur_route_start = cur_route_start->next_edge)) break;
	 }
      }
      free_net(n);
   }

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
      disp_vrp_tour(window, TRUE, name, tour, vrp->vertnum, vrp->numroutes,
		    CTOI_WAIT_FOR_CLICK_AND_REPORT);
   }

#ifndef WIN32
   if (window){
      char name[MAX_NAME_LENGTH] = {"feas_solution"};
      disp_vrp_tour(window, TRUE, name, tour, vrp->vertnum, vrp->numroutes,
		    CTOI_WAIT_FOR_CLICK_AND_REPORT);
   }
#endif
   
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
   vrp_problem *vrp = (vrp_problem *)user;

   *feas_sol_size = vrp->feas_sol_size;
   *feas_sol = vrp->feas_sol;
#endif
   return(USER_SUCCESS);
}   

/*===========================================================================*/

/*===========================================================================*\
 * This function frees everything.
\*===========================================================================*/

int user_free_master(void **user)
{
   vrp_problem *vrp = (vrp_problem *)(*user);

   if (vrp->cur_tour){
      FREE(vrp->cur_tour->tour);
      FREE(vrp->cur_tour->route_info);
      FREE(vrp->cur_tour);
   }
   FREE(vrp->posy);
   FREE(vrp->posx);
   FREE(vrp->dist.coordx);
   FREE(vrp->dist.coordy);
   FREE(vrp->dist.coordz);
#if !(defined(COMPILE_IN_TM) && defined(COMPILE_IN_LP))
   FREE(vrp->dist.cost);
   FREE(vrp->edges);
   FREE(vrp->demand);
#endif
#ifdef COMPILE_HEURS
   if (vrp->tours){
      FREE(vrp->tours[0].tour);
      if (vrp->tourorder)
	 for (i=0; i<=vrp->tournum; i++)
	    FREE(vrp->tours[vrp->tourorder[i]].route_info);
      FREE(vrp->tours);
   }
   FREE(vrp->tourorder);
   if (vrp->lb){
      FREE(vrp->lb->tree);
      FREE(vrp->lb->best_edges);
      FREE(vrp->lb);
   }
   FREE(vrp->par.rand_seed);
#endif
   if (vrp->g){
      FREE(vrp->g->edges);
      FREE(vrp->g);
   }
#ifdef CHECK_CUT_VALIDITY
   FREE(vrp->feas_sol);
#endif
   FREE(vrp->zero_vars);
   FREE(vrp);

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






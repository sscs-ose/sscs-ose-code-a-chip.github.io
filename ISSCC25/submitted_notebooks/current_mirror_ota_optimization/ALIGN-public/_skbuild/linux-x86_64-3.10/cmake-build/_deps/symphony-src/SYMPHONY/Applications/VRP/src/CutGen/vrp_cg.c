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
#include <stdlib.h>
#include <string.h>

/* SYMPHONY include files */
#include "sym_macros.h"
#include "sym_constants.h"
#include "sym_proccomm.h"
#include "sym_cg_u.h"

/* VRP include files */
#include "vrp_cg.h"
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef COMPILE_DECOMP
#include "my_decomp.h"
#include "decomp.h"
#endif
#include "sym_dg_params.h"
#include "vrp_dg.h"
/*___END_EXPERIMENTAL_SECTION___*/
#include "vrp_macros.h"
#include "vrp_const.h"

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
#include "util.h"
CCrandstate rand_state;
#endif
/*___END_EXPERIMENTAL_SECTION___*/

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
   int i, j, k;
   /* This is the user-defined data structure, a pointer to which will
      be passed to each user function. It must contain all the
      problem-specific data needed for computations within the CG */
   vrp_cg_problem *vrp = (vrp_cg_problem *) malloc(sizeof(vrp_cg_problem));
   int edgenum;

   *user = vrp;

   vrp->n = NULL;

   /*------------------------------------------------------------------------*\
    * Receive the data
   \*------------------------------------------------------------------------*/
   
   receive_char_array((char *)(&vrp->par), sizeof(vrp_cg_params));
   
   receive_int_array(&vrp->dg_id, 1);
   receive_int_array(&vrp->numroutes, 1);
   receive_int_array(&vrp->vertnum, 1);
   vrp->demand = (int *) calloc(vrp->vertnum, sizeof(int));
   receive_int_array(vrp->demand, vrp->vertnum);
   receive_int_array(&vrp->capacity, 1);
   edgenum = vrp->vertnum*(vrp->vertnum-1)/2;
#ifdef CHECK_CUT_VALIDITY
   receive_int_array(&vrp->feas_sol_size, 1);
   if (vrp->feas_sol_size){
      vrp->feas_sol = (int *) calloc(vrp->feas_sol_size, sizeof(int));
      receive_int_array(vrp->feas_sol, vrp->feas_sol_size);
   }
#endif

   /*------------------------------------------------------------------------*\
    * Set up some data structures
   \*------------------------------------------------------------------------*/

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef COMPILE_OUR_DECOMP   
   if (vrp->par.do_our_decomp){
      vrp->cost = (int *) calloc(edgenum, sizeof(int));
      receive_int_array(vrp->cost, edgenum);
      usr_open_decomp_lp( get_cg_ptr(NULL), edgenum );
   }

   vrp->last_decomp_index = -1;
#endif   
/*___END_EXPERIMENTAL_SECTION___*/
   vrp->in_set = (char *) calloc(vrp->vertnum, sizeof(char));
   vrp->ref = (int *) malloc(vrp->vertnum*sizeof(int));
   vrp->new_demand = (int *) malloc(vrp->vertnum*sizeof(int));
   vrp->cut_val = (double *) calloc(vrp->vertnum, sizeof(double));
   vrp->cut_list = (char *) malloc(((vrp->vertnum >> DELETE_POWER)+1)*
				   (vrp->par.max_num_cuts_in_shrink + 1)*
				   sizeof(char));
   
   vrp->edges = (int *) calloc(2*edgenum, sizeof(int));

   /*create the edge list (we assume a complete graph)*/
   for (i = 1, k = 0; i < vrp->vertnum; i++){
      for (j = 0; j < i; j++){
	 vrp->edges[k << 1] = j;
	 vrp->edges[(k << 1) + 1] = i;
	 k++;
      }
   }

   vrp->dg_id = dg_id;

   return(USER_SUCCESS);
}

/*===========================================================================*/

int user_receive_lp_solution_cg(void *user)
{
   /* Leave this job to SYMPHONY. We don't need anything special */
   return(USER_DEFAULT);
}

/*===========================================================================*/

/*===========================================================================*\
 * Free the user data structure
\*===========================================================================*/

int user_free_cg(void **user)
{
   vrp_cg_problem *vrp = (vrp_cg_problem *)(*user);

#if defined(CHECK_CUT_VALIDITY) && !defined(COMPILE_IN_TM)
   if (vrp->feas_sol_size)
      FREE(vrp->feas_sol);
#endif
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef COMPILE_OUR_DECOMP
#if !defined(COMPILE_IN_CG) 
   if (vrp->par.do_our_decomp){
      close_decomp_lp( get_cg_ptr(NULL) );
      FREE(vrp->cost);
   }
#endif
   CClp_close();
#endif
/*___END_EXPERIMENTAL_SECTION___*/
#pragma omp master
   {
#if 0
      FREE(vrp->demand);
      FREE(vrp->edges);
      FREE(vrp->in_set);
      FREE(vrp->ref);
      FREE(vrp->new_demand);
      FREE(vrp->cut_val);
      FREE(vrp->cut_list);
   
      FREE(*user);
#endif
   }

   return(USER_SUCCESS);
}

/*===========================================================================*/

/*===========================================================================*\
 * Find cuts violated by a particular LP solution. This is a fairly
 * involved function but the bottom line is that an LP solution comes in
 * and cuts go out.
\*===========================================================================*/

int user_find_cuts(void *user, int varnum, int iter_num, int level,
		   int index, double objval, int *indices, double *values,
		   double ub, double etol, int *num_cuts, int *alloc_cuts,
		   cut_data ***cuts)
{
   vrp_cg_problem *vrp = (vrp_cg_problem *)user;
   int vertnum = vrp->vertnum;
   network *n;
   vertex *verts = NULL;
   int *compdemands = NULL, *compnodes = NULL, *compnodes_copy = NULL;
   int *compmembers = NULL, comp_num = 0;
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   int *compdemands_copy = NULL;
   double *compcuts_copy = NULL, *compdensity = NULL, density;
   /*___END_EXPERIMENTAL_SECTION___*/
   double node_cut, max_node_cut, *compcuts = NULL;
   int rcnt, cur_bins = 0, k;
   char **coef_list;
   int i, max_node;
   double cur_slack = 0.0;
   int capacity = vrp->capacity;
   int cut_size = (vertnum >> DELETE_POWER) + 1;
   cut_data *new_cut = NULL;
   elist *cur_edge = NULL;
   int which_connected_routine = vrp->par.which_connected_routine;
   int *ref = vrp->ref;
   double *cut_val = vrp->cut_val;
   char *in_set = vrp->in_set;
   char *cut_list = vrp->cut_list;

   elist *cur_edge1 = NULL, *cur_edge2 = NULL;
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef COMPILE_OUR_DECOMP
   edge *edge_pt;
#endif
/*___END_EXPERIMENTAL_SECTION___*/
   int node1 = 0, node2 = 0;
   int *demand = vrp->demand;
   int *new_demand = vrp->new_demand;
   int total_demand = demand[0]; 
   int num_routes = vrp->numroutes, num_trials;
   int triangle_cuts = 0;
   char *coef; 

   if (iter_num == 1) SRANDOM(1);
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
   CCutil_sprand(1, &rand_state);
#endif
/*___END_EXPERIMENTAL_SECTION___*/
   
/*__BEGIN_EXPERIMENTAL_SECTION__*/

#if 0   
   if (vrp->dg_id && vrp->par.verbosity > 3){
      sprintf(name, "support graph");
      display_support_graph(vrp->dg_id, (p->cur_sol.xindex == 0 &&
			    p->cur_sol.xiter_num == 1) ? TRUE: FALSE, name,
			    varnum, xind, xval,
			    etol, CTOI_WAIT_FOR_CLICK_AND_REPORT);
   }      
#endif
/*___END_EXPERIMENTAL_SECTION___*/
   
   /* This creates a fractional graph representing the LP solution */
   n = createnet(indices, values, varnum, etol, vrp->edges, demand, vertnum);
   if (n->is_integral){
      /* if the network is integral, check for connectivity */
      check_connectivity(n, etol, capacity, num_routes, cuts, num_cuts,
			 alloc_cuts);
      free_net(n);
      return(USER_SUCCESS);
   }

#ifdef DO_TSP_CUTS
   if (vrp->par.which_tsp_cuts && vrp->par.tsp_prob){
      tsp_cuts(n, vrp->par.verbosity, vrp->par.tsp_prob,
	       vrp->par.which_tsp_cuts, cuts, num_cuts, alloc_cuts);
      free_net(n);
      return(USER_SUCCESS);
   }      
#endif
   
/*__BEGIN_EXPERIMENTAL_SECTION__*/
   if (!vrp->par.always_do_mincut){/*user_par.always_do_mincut indicates
				     whether we should just always do the
				     min_cut routine or whether we should also
				     try this routine*/
/*___END_EXPERIMENTAL_SECTION___*/
/*UNCOMMENT FOR PRODUCTION CODE*/
#if 0
   {
#endif
      verts = n->verts;
      if (which_connected_routine == BOTH)
	 which_connected_routine = CONNECTED;
      
      new_cut = (cut_data *) calloc(1, sizeof(cut_data));
      new_cut->size = cut_size;
      compnodes_copy = (int *) malloc((vertnum + 1) * sizeof(int));
      compmembers = (int *) malloc((vertnum + 1) * sizeof(int));
      /*__BEGIN_EXPERIMENTAL_SECTION__*/
      compdemands_copy = (int *) calloc(vertnum + 1, sizeof(int));
      compcuts_copy = (double *) calloc(vertnum + 1, sizeof(double));
#ifdef COMPILE_OUR_DECOMP
      compdensity = vrp->par.do_our_decomp ?
	 (double *) calloc(vertnum+1, sizeof(double)) : NULL;
#endif
      /*___END_EXPERIMENTAL_SECTION___*/
      
      do{
	 compnodes = (int *) calloc(vertnum + 1, sizeof(int));
	 compdemands = (int *) calloc(vertnum + 1, sizeof(int));
	 compcuts = (double *) calloc(vertnum + 1, sizeof(double));
	 
         /*------------------------------------------------------------------*\
          * Get the connected components of the solution graph without the
          * depot and see if the number of components is more than one
         \*------------------------------------------------------------------*/
	 rcnt = (which_connected_routine == BICONNECTED ?
		      biconnected(n, compnodes, compdemands, compcuts) :
		      connected(n, compnodes, compdemands, compmembers,
				/*__BEGIN_EXPERIMENTAL_SECTION__*/
				compcuts, compdensity));
	                        /*___END_EXPERIMENTAL_SECTION___*/
	                        /*UNCOMMENT FOR PRODUCTION CODE*/
#if 0
				compcuts, NULL));
#endif

	 /* copy the arrays as they will be needed later */
	 if (!which_connected_routine &&
	     /*__BEGIN_EXPERIMENTAL_SECTION__*/
	     (vrp->par.do_greedy || vrp->par.do_our_decomp)){
	    /*___END_EXPERIMENTAL_SECTION___*/
	    /*UNCOMMENT FOR PRODUCTION CODE*/
#if 0
	    vrp->par.do_greedy){
#endif
	    compnodes_copy = (int *) memcpy((char *)compnodes_copy, 
					    (char*)compnodes,
					    (vertnum+1)*sizeof(int));
	    /*__BEGIN_EXPERIMENTAL_SECTION__*/
	    compdemands_copy = (int *) memcpy((char *)compdemands_copy,
				       (char *)compdemands, (vertnum+1)*ISIZE);
	    compcuts_copy = (double *) memcpy((char *)compcuts_copy,
					      (char *)compcuts,
					      (vertnum+1)*DSIZE);
	    /*___END_EXPERIMENTAL_SECTION___*/
	    n->compnodes = compnodes_copy;
	    comp_num = rcnt;
	 }
	 if (rcnt > 1){
	    /*---------------------------------------------------------------*\
	     * If the number of components is more then one, then check each
	     * component to see if it violates a capacity constraint
	    \*---------------------------------------------------------------*/
	    
	    coef_list = (char **) calloc(rcnt, sizeof(char *));
	    coef_list[0] = (char *) calloc(rcnt*cut_size, sizeof(char));
	    for(i = 1; i<rcnt; i++)
	       coef_list[i] = coef_list[0]+i*cut_size;
	    
	    for(i = 1; i < vertnum; i++)
	       (coef_list[(verts[i].comp)-1][i >> DELETE_POWER]) |=
		  (1 << (i & DELETE_AND));
	    
	    for (i = 0; i < rcnt; i++){
	       if (compnodes[i+1] < 2) continue;
	       /*check ith component to see if it violates a constraint*/
	       if (vrp->par.which_connected_routine == BOTH &&
		   which_connected_routine == BICONNECTED && compcuts[i+1]==0)
		  continue;
	       if (compcuts[i+1] < 2*BINS(compdemands[i+1], capacity)-etol){
		  /*the constraint is violated so impose it*/
		  new_cut->coef = (char *) (coef_list[i]);
		  new_cut->type = (compnodes[i+1] < vertnum/2 ?
				 SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
		  new_cut->rhs = (new_cut->type == SUBTOUR_ELIM_SIDE ?
				  RHS(compnodes[i+1],compdemands[i+1],
				      capacity): 2*BINS(compdemands[i+1],
							capacity));
		  cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	       }
	       else{/*if the constraint is not violated, then try generating a
		      violated constraint by deleting customers that don't
		      change the number of trucks required by the customers in
		      the component but decrease the value of the cut*/
		  cur_bins = BINS(compdemands[i+1], capacity);/*the current
						    number of trucks required*/
		  /*current slack in the constraint*/
		  cur_slack = (compcuts[i+1] - 2*cur_bins);
		  while (compnodes[i+1]){/*while there are still nodes in the
					   component*/
		     for (max_node = 0, max_node_cut = 0, k = 1;
			  k < vertnum; k++){
			if (verts[k].comp == i+1){
			   if (BINS(compdemands[i+1]-verts[k].demand, capacity)
			       == cur_bins){
			      /*if the number of trucks doesn't decrease upon
				deleting this customer*/
			      for (node_cut = 0, cur_edge = verts[k].first;
				   cur_edge; cur_edge = cur_edge->next_edge){
				 node_cut += (cur_edge->other_end ?
					      -cur_edge->data->weight :
					      cur_edge->data->weight);
			      }
			      if (node_cut > max_node_cut){/*check whether the
					 value of the cut decrease is the best
					 seen so far*/
				 max_node = k;
				 max_node_cut = node_cut;
			      }
			   }
			}
		     }
		     if (!max_node){
			break;
		     }
		     /*delete the customer that exhibited the greatest
		       decrease in cut value*/
		     compnodes[i+1]--;
		     compdemands[i+1] -= verts[max_node].demand;
		     compcuts[i+1] -= max_node_cut;
		     cur_slack -= max_node_cut;
		     verts[max_node].comp = 0;
		     coef_list[i][max_node >> DELETE_POWER] ^=
			(1 << (max_node & DELETE_AND));
		     if (cur_slack < 0){/*if the cut is now violated, impose
					  it*/
			new_cut->coef = (char *) (coef_list[i]);
			new_cut->type = (compnodes[i+1] < vertnum/2 ?
				       SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
			new_cut->size = cut_size;
			new_cut->rhs = (new_cut->type == SUBTOUR_ELIM_SIDE ?
					RHS(compnodes[i+1], compdemands[i+1],
					    capacity): 2*cur_bins);
			cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
			break;
		     }
		  }
	       }
	    }
	    FREE(coef_list[0]);
	    FREE(coef_list);
	 }
	 which_connected_routine++;
	 FREE(compnodes);
	 FREE(compdemands);
	 FREE(compcuts);
      }while((!(*num_cuts) && vrp->par.which_connected_routine == BOTH)
	     && which_connected_routine < 2);
   }

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
   if (!*(num_cuts) && vrp->par.do_mincut){
      min_cut(vrp, n, etol);
   }
#endif
   
   if (!vrp->par.do_greedy && !vrp->par.do_our_decomp){
/*___END_EXPERIMENTAL_SECTION___*/
/*UNCOMMENT FOR PRODUCTION CODE*/
#if 0
   if (!vrp->par.do_greedy){
#endif
      free_net(n);
      return(USER_SUCCESS);
   }

   if (*num_cuts < 10 && vrp->par.do_greedy){
      coef = (char *) malloc(cut_size * sizeof(char)); 
      for (cur_edge=verts[0].first; cur_edge; cur_edge=cur_edge->next_edge){
	 for (cur_edge1 = cur_edge->other->first; cur_edge1;
	      cur_edge1 = cur_edge1->next_edge){
	    if (cur_edge1->data->weight + cur_edge->data->weight < 1 - etol)
	       continue; 
	    node1 = cur_edge->other_end; 
	    node2 = cur_edge1->other_end;
	    for (cur_edge2 = verts[node2].first; cur_edge2;
		 cur_edge2 = cur_edge2->next_edge){
	       if (!(cur_edge2->other_end) && node2){
		  if ((BINS(total_demand - demand[node1] - demand[node2],
			    capacity) > num_routes -1) &&
		      (cur_edge1->data->weight + cur_edge->data->weight +
		       cur_edge2->data->weight>2+etol)){
		     new_cut->type = SUBTOUR_ELIM_ACROSS;
		     new_cut->size =cut_size;
		     new_cut->rhs =2*BINS(total_demand - demand[node1] -
					  demand[node2],capacity);
		     memset(coef, 0, cut_size);
		     for (i = 1; i <vertnum ; i++)
			if ((i != node1) && (i != node2))
			   (coef[i >> DELETE_POWER]) |= (1 << (i&DELETE_AND));
		     new_cut->coef =coef;
		     triangle_cuts += cg_send_cut(new_cut, num_cuts, alloc_cuts,
						  cuts);
		  }
		  break; 
	       }
	    }
	 }
      }
      FREE(coef);
      if (vrp->par.verbosity > 2)
	 printf("Found %d triangle cuts\n",triangle_cuts);
   }

   if (*num_cuts < 10 && vrp->par.do_greedy){
      memcpy((char *)new_demand, (char *)demand, vertnum*ISIZE);
      reduce_graph(n, etol, new_demand);
      if (comp_num > 1){
	 greedy_shrinking1(n, capacity, etol,
			   vrp->par.max_num_cuts_in_shrink,
			   new_cut, compnodes_copy, compmembers,
			   comp_num, in_set, cut_val,
			   ref, cut_list, new_demand, cuts,
			   num_cuts, alloc_cuts);
      }else{
	 greedy_shrinking1_one(n, capacity, etol,
			       vrp->par.max_num_cuts_in_shrink,
			       new_cut, in_set, cut_val, cut_list,
			       num_routes, new_demand, cuts,
			       num_cuts, alloc_cuts);
      }
   }

   if (*num_cuts < 10 && vrp->par.do_greedy){
      if (vrp->par.do_extra_in_root)
	 num_trials = level ? vrp->par.greedy_num_trials :
	                       2 * vrp->par.greedy_num_trials;
      else
	 num_trials = vrp->par.greedy_num_trials;
      if (comp_num){
	 greedy_shrinking6(n, capacity, etol, new_cut,
			   compnodes_copy, compmembers, comp_num,
			   in_set, cut_val, ref, cut_list,
			   vrp->par.max_num_cuts_in_shrink,
			   new_demand, num_cuts ? num_trials :
			   2 * num_trials, 10.5, cuts,
			   num_cuts, alloc_cuts);
      }else{
	 greedy_shrinking6_one(n, capacity, etol, new_cut, in_set,
			       cut_val, num_routes, cut_list,
			       vrp->par.max_num_cuts_in_shrink,
			       new_demand, num_cuts ? num_trials :
			       2 * num_trials, 10.5, cuts,
			       num_cuts, alloc_cuts); 
      }
   }
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0    
   if (!(*num_cuts) && comp_num==1){
      greedy_shrinking2_one(n, capacity, etol, new_cut, in_set,
			    cut_val, num_routes, new_demand, cuts
			    num_cuts, alloc_cuts);
   }
#endif
/*___END_EXPERIMENTAL_SECTION___*/

#ifdef DO_TSP_CUTS
   if (!(*num_cuts) && vrp->par.which_tsp_cuts){
      tsp_cuts(n, vrp->par.verbosity, vrp->par.tsp_prob,
	       vrp->par.which_tsp_cuts, cuts, num_cuts, alloc_cuts);
   }
#endif
   
/*__BEGIN_EXPERIMENTAL_SECTION__*/
   FREE(compdemands_copy);
   FREE(compcuts_copy);
   density = n->edgenum/n->vertnum;
/*___END_EXPERIMENTAL_SECTION___*/
   FREE(compmembers);
   FREE(new_cut);
   free_net(n);

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#ifdef COMPILE_OUR_DECOMP
   if (!(*num_cuts) &&  vrp->par.do_our_decomp &&
       (vrp->last_decomp_index != index ||
	(vrp->last_decomp_index == index &&
	 (objval - vrp->last_objval)/ub >= vrp->par.gap_threshold))){
      if (!vrp->par.decomp_decompose){
	 comp_num = 1;
	 compdensity[1] = density;
	 compnodes_copy[1] = vertnum - 1;
      }
      for (i = 1; i <= comp_num; i++){
	 if (compdensity[i] < vrp->par.graph_density_threshold &&
	     compnodes_copy[i] > 3){
	    vrp->last_decomp_index = index;
	    vrp->last_objval = objval;
#if 0
	    ind_sort(indices, values, varnum);*/
#endif
	    /*need to recreate the network as it has been altered*/
	    vrp->n = n = status ? createnet2(indices, values, varnum, etol,
					     vrp->edges, demand, vertnum,
					     status) :
	                          createnet(indices, values, varnum, etol,
					    vrp->edges, demand, vertnum);

	    /* fill out the cost fields */
	    for (edge_pt=n->edges+n->edgenum-1; edge_pt >= n->edges; edge_pt--)
	       edge_pt->cost = vrp->cost[INDEX(edge_pt->v0, edge_pt->v1)];
	    
#if 0
	    aux = n->edgenum-n->verts[0].degree;
	    aux /= n->vertnum;
	    printf("Calling decomp: density %f , depot degree %d, obj %f, ",
		   aux, n->verts[0].degree, p->cur_sol.objval);
	    printf("level %d  \n", p->cur_sol.xlevel);
	    fprintf("Calling decomp: density %f , depot degree %d, obj %f, ",
		    aux, n->verts[0].degree, p->cur_sol.objval);
	    fprintf("level %d  \n", p->cur_sol.xlevel);
#endif
	    vrp_decomp(comp_num, compdensity);
	    free_net(n);
	    break;
	 }
      }
   }
#endif

   FREE(compdensity);
/*___END_EXPERIMENTAL_SECTION___*/
   FREE(compnodes_copy);
   
   return(USER_SUCCESS);
}

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
/*This is the original version*/
int user_find_cuts(void *user, int xlength, int *xind,
		   double *xval, double etol, int *pnumcuts)
{
   vrp_cg_problem *vrp = (vrp_cg_problem *)user;
   int vertnum = vrp->vertnum;
   network *n;
   vertex *verts;
   int *compdemands = NULL;
   double *compcuts = NULL, node_cut, max_node_cut;
   int rcnt, cur_bins = 0, k;
   char **coef_list, name[20];
   int i, *compnodes = NULL, max_node;
   int num_cuts = 0;
   double cur_slack = 0.0;
   int capacity = vrp->capacity;
   int cut_size = (vrp->vertnum >> DELETE_POWER) + 1;
   cut_data *new_cut;
   elist *cur_edge = NULL;
   int which_connected_routine = vrp->par.which_connected_routine;
   
   if (vrp->dg_id && vrp->par.verbosity > 3){
      sprintf(name, "support graph");
      /*display_support_graph(vrp->dg_id, (p->cur_sol->xindex == 0 &&
			    p->cur_sol->xiter_num == 1) ? TRUE: FALSE, name,
			    p->cur_sol->xlength, p->cur_sol->xind,
			    p->cur_sol->xval,
			    etol, CTOI_WAIT_FOR_CLICK_AND_REPORT);*/
   }      

   /*create the solution graph*/
   n = createnet(xind, xval, xlength, etol, vrp->edges, vrp->demand,
		 vrp->vertnum);
   if (n->is_integral){ /*if the network is integral, check for feasibility*/
      /* Feasibility is already tested in the LP process, thus in this
       * case we are just checking for connectivity and violation of
       * capacity constraints*/
      num_cuts = check_feasibility(n, xind, xval, xlength, etol, capacity,
				   numroutes);
      free_net(n);
      *pnumcuts = num_cuts;
      return(USER_SUCCESS);
   }
   
   if (!vrp->par.always_do_mincut){/*user_par.always_do_mincut indicates
				     whether we should just always do the
				     min_cut routine or whether we should also
				     try this routine*/
      verts = n->verts;
      if (which_connected_routine == BOTH)
	 which_connected_routine = CONNECTED;
      
      new_cut = (cut_data *) calloc(1, sizeof(cut_data));
      new_cut->size = cut_size;
      do{
	 compnodes = (int *) calloc(vertnum + 1, sizeof(int));
	 compdemands = (int *) calloc(vertnum + 1, sizeof(int));
	 compcuts = (double *) calloc(vertnum + 1, sizeof(double));
	 
	 /*------------------------------------------------------------------*\
         | Get the connected components of the solution graph without the     |
	 | depot and see if the number of components is more than one         |
	 \*------------------------------------------------------------------*/
	 if ((rcnt = (which_connected_routine == BICONNECTED?
		      biconnected(n, compnodes, compdemands, compcuts) :
		      connected(n, compnodes, compdemands, NULL, compcuts))) > 1){
	    
	    /*---------------------------------------------------------------*\
            | If the number of components is more then one, then check each   |
	    | component to see if it violates a capacity constraint           |
	    \*---------------------------------------------------------------*/
	    
	    coef_list = (char **) calloc(rcnt, sizeof(char *));
	    coef_list[0] = (char *) calloc(rcnt*cut_size, sizeof(char));
	    for(i = 1; i<rcnt; i++)
	       coef_list[i] = coef_list[0]+i*cut_size;
	    
	    for(i = 1; i < vertnum; i++)
	       (coef_list[(verts[i].comp)-1][i >> DELETE_POWER]) |=
		  (1 << (i & DELETE_AND));
	    
	    for (i = 0; i < rcnt; i++){
	       if (compnodes[i+1] < 2) continue;
	       /*check ith component to see if it violates a constraint*/
	       if (vrp->par.which_connected_routine == BOTH &&
		   which_connected_routine == BICONNECTED && compcuts[i+1]==0)
		  continue;
	       if (compcuts[i+1] < 2*BINS(compdemands[i+1], capacity)-etol){
		  /*the constraint is violated so impose it*/
		  new_cut->coef = (char *) (coef_list[i]);
		  new_cut->type = (compnodes[i+1] < vertnum/2 ?
				 SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
		  new_cut->rhs = (new_cut->type == SUBTOUR_ELIM_SIDE ?
				  RHS(compnodes[i+1],compdemands[i+1],
				      capacity): 2*BINS(compdemands[i+1],
							capacity));
		  cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	       }
	       else{/*if the constraint is not violated, then try generating a
		      violated constraint by deleting customers that don't
		      change the number of trucks required by the customers in
		      the component but decrease the value of the cut*/
		  cur_bins = BINS(compdemands[i+1], capacity);/*the current
						    number of trucks required*/
		  cur_slack = compcuts[i+1] - 2*cur_bins;/*current slack in the
							   constraint*/
		  while (compnodes[i+1]){/*while there are still nodes in the
					   component*/
		     for (max_node = 0, max_node_cut = 0, k = 1;
			  k<vertnum; k++){
			if (verts[k].comp == i+1){
			   if (BINS(compdemands[i+1]-verts[k].demand, capacity)
			       == cur_bins){
			      /*if the number of trucks doesn't decrese upon
				deleting this customer*/
			      for (node_cut = 0, cur_edge = verts[k].first;
				   cur_edge; cur_edge = cur_edge->next_edge){
				 node_cut += (cur_edge->other_end ?
					      -cur_edge->data->weight :
					      cur_edge->data->weight);
			      }
			      if (node_cut > max_node_cut){/*check whether the
					 value of the cut decrease is the best
					 seen so far*/
				 max_node = k;
				 max_node_cut = node_cut;
			      }
			   }
			}
		     }
		     if (!max_node){
			break;
		     }
		     /*delete the customer that exhibited the greatest
		       decrease in cut value*/
		     compnodes[i+1]--;
		     compdemands[i+1] -= verts[max_node].demand;
		     compcuts[i+1] -= max_node_cut;
		     cur_slack -= max_node_cut;
		     verts[max_node].comp = 0;
		     coef_list[i][max_node >> DELETE_POWER] ^=
			(1 << (max_node & DELETE_AND));
		     if (cur_slack < 0){/*if the cut is now violated, impose
					  it*/
			new_cut->coef = (char *) (coef_list[i]);
			new_cut->type = (compnodes[i+1] < vertnum/2 ?
				       SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
			new_cut->size = cut_size;
			new_cut->rhs = (new_cut->type == SUBTOUR_ELIM_SIDE ?
					RHS(compnodes[i+1], compdemands[i+1],
					    capacity): 2*cur_bins);
			cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
			break;
		     }
		  }
	       }
	    }
	    FREE(coef_list[0]);
	    FREE(coef_list);
	 }
	 which_connected_routine++;
	 FREE(compnodes);
	 FREE(compdemands);
	 FREE(compcuts);
      }while((!num_cuts || vrp->par.which_connected_routine == BOTH)
	     && which_connected_routine < 2);
      FREE(new_cut);
   }
   if (num_cuts){/*if we found some cuts using the above routines, then exit*/
      free_net(n);
      *pnumcuts = num_cuts;
      return(USER_SUCCESS);
   }
   else{/*if we still haven't found any cuts, then try the min cut routine*/
      num_cuts = min_cut(vrp, n, etol);/*find cuts using min cut routine*/
      free_net(n);
      *pnumcuts = num_cuts;
      return(USER_SUCCESS);
   }
}
#endif

/*___END_EXPERIMENTAL_SECTION___*/
/*===========================================================================*/
  
/*===========================================================================*\
 * This routine takes a solution which is integral and checkes whether it is
 * feasible by first checking if it is connected and then checking to make
 * sure each route obeys the capacity constraints.
\*===========================================================================*/

void check_connectivity(network *n, double etol, int capacity, int numroutes,
		       cut_data ***cuts, int *num_cuts, int *alloc_cuts)
{
  vertex *verts;
  elist *cur_route_start;
  int weight = 0, reduced_weight, *compdemands, *route;
  edge *edge_data;
  int cur_vert = 0, prev_vert, cust_num = 0, cur_route, rcnt, *compnodes;
  cut_data *new_cut;
  char **coef_list;
  int i, reduced_cust_num;
  int vertnum = n->vertnum, vert1, vert2;
  int cut_size = (vertnum >> DELETE_POWER) +1;
  double *compcuts;
  
  if (!n->is_integral) return;

  verts = n->verts;
  compnodes = (int *) calloc(vertnum + 1, sizeof(int));
  compdemands = (int *) calloc(vertnum + 1, sizeof(int));
  compcuts = (double *) calloc(vertnum + 1, sizeof(double));
  /*get the components of the solution graph without the depot to check if the
    graph is connected or not*/
  rcnt = connected(n, compnodes, compdemands, NULL, compcuts, NULL);
  coef_list = (char **) calloc(rcnt, sizeof(char *));
  coef_list[0] = (char *) calloc(rcnt*cut_size, sizeof(char));
  for(i = 1; i<rcnt; i++)
     coef_list[i] = coef_list[0]+i*cut_size;

  for(i = 1; i < vertnum; i++)
    (coef_list[(verts[i].comp)-1][i >> DELETE_POWER]) |=
      (1 << (i & DELETE_AND));
  
  /*-------------------------------------------------------------------------*\
  | For each component check to see if the cut it induces is nonzero -- each  |
  | component's cut value must be either 0 or 2 since we have integrality     |
  \*-------------------------------------------------------------------------*/
  
  new_cut = (cut_data *) calloc(1, sizeof(cut_data));
  new_cut->size = cut_size;
  for (i = 0; i<rcnt; i++){
    if (compcuts[i+1] < etol){/*if the cut value is zero, the graph is
				disconnected and we have a violated cut*/
      new_cut->coef = (char *) (coef_list[i]);
      new_cut->type = (compnodes[i+1] < vertnum/2 ?
		       SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
      new_cut->rhs = (new_cut->type == SUBTOUR_ELIM_SIDE ?
		      RHS(compnodes[i+1], compdemands[i+1], capacity):
		      2*BINS(compdemands[i+1], capacity));
      cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
    }
  }

  FREE(coef_list[0]);
  FREE(coef_list);
  FREE(compnodes);
  FREE(compdemands);
  FREE(compcuts);

  /*-------------------------------------------------------------------------*\
  | if the graph is connected, check each route to see if it obeys the        |
  | capacity constraints                                                      |
  \*-------------------------------------------------------------------------*/

  route = (int *) malloc(vertnum*ISIZE);
  for (cur_route_start = verts[0].first, cur_route = 0,
       edge_data = cur_route_start->data; cur_route < numroutes;
       cur_route++){
    edge_data = cur_route_start->data;
    edge_data->scanned = TRUE;
    cur_vert = edge_data->v1;
    prev_vert = weight = cust_num = 0;

    new_cut->coef = (char *) calloc(cut_size, sizeof(char));

    route[0] = cur_vert;
    while (cur_vert){
                    /*keep tracing around the route and whenever the addition
		       of the next customer causes a violation, impose the
		       constraint induced
		       by the set of customers seen so far on the route*/
      new_cut->coef[cur_vert >> DELETE_POWER]|=(1 << (cur_vert & DELETE_AND));
      cust_num++;
      if ((weight += verts[cur_vert].demand) > capacity){
	new_cut->type = (cust_num < vertnum/2 ?
			 SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	new_cut->rhs = (new_cut->type ==SUBTOUR_ELIM_SIDE ?
			RHS(cust_num, weight, capacity):
			2*BINS(weight, capacity));
	cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	vert1 = route[0];
	reduced_weight = weight;
	reduced_cust_num = cust_num;
	while (TRUE){
	  if ((reduced_weight -= verts[vert1].demand) > capacity){
	     reduced_cust_num--;
	     new_cut->coef[vert1 >> DELETE_POWER] &=
		~(1 << (vert1 & DELETE_AND));
	     new_cut->type = (reduced_cust_num < vertnum/2 ?
			      SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	     new_cut->rhs = (new_cut->type ==SUBTOUR_ELIM_SIDE ?
			     RHS(reduced_cust_num, reduced_weight, capacity):
			     2*BINS(reduced_weight, capacity));
	     cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	     vert1 = route[vert1];
	  }else{
	     break;
	  }
	}
	vert2 = route[0];
	while (vert2 != vert1){
	  new_cut->coef[vert2 >> DELETE_POWER] |=
	     (1 << (vert2 & DELETE_AND));
	  vert2 = route[vert2];
	}
      }
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
      route[prev_vert] = cur_vert;
    }
    edge_data->scanned = TRUE;

    FREE(new_cut->coef);
    
    while (cur_route_start->data->scanned){/*find the next edge leading out of
					     the depot which has not yet been
					     traversed to start the next
					     route*/
      if (!(cur_route_start = cur_route_start->next_edge)) break;
    }
  }
  FREE(route);
  FREE(new_cut);
  
  for (cur_route_start = verts[0].first; cur_route_start;
       cur_route_start = cur_route_start->next_edge)
    cur_route_start->data->scanned = FALSE;
}

/*__BEGIN_EXPERIMENTAL_SECTION__*/
/*===========================================================================*/

#ifdef COMPILE_DECOMP
void user_send_to_sol_pool(cg_prob *p)
{
#if 0
   int size = p->cur_sol.xlength*sizeof(int);
   int s_bufid;
   
   if (p->sol_pool){
      s_bufid = init_send(DataInPlace);
      send_int_array(&size, 1);
      send_int_array(&p->cur_sol.xlevel, 1);
      send_char_array((char *)(p->cur_sol.xind), size);
      send_msg(p->sol_pool, PACKED_COL);
      freebuf(s_bufid);
   }
#endif
}
#endif

/*___END_EXPERIMENTAL_SECTION___*/
/*===========================================================================*/

/*===========================================================================*\
 * This is an undocumented (for now) debugging feature which can allow the user
 * to identify the cut which cuts off a particular known feasible solution.
\*===========================================================================*/

#ifdef CHECK_CUT_VALIDITY
/*__BEGIN_EXPERIMENTAL_SECTION__*/

#include "sym_cg.h"
/*___END_EXPERIMENTAL_SECTION___*/

int user_check_validity_of_cut(void *user, cut_data *new_cut)
{
   vrp_cg_problem *vrp = (vrp_cg_problem *)user;
   int *edges = vrp->edges;
   int *feas_sol = vrp->feas_sol;
   double lhs = 0;
   char *coef;
   int v0, v1;
   int i, j, vertnum = vrp->vertnum;
   int size, cliquecount = 0;
   char *clique_array; 
   /*__BEGIN_EXPERIMENTAL_SECTION__*/
   
   int num_arcs, edge_index ; 
   char *cpt; 
   int *arcs ;
   char *indicators;
   double bigM, *weights ;
   int jj, num_fracs, fracs;
   /*___END_EXPERIMENTAL_SECTION___*/
   
   if (vrp->feas_sol_size){
      switch (new_cut->type){
	 
	 /*------------------------------------------------------------------*\
	  * The subtour elimination constraints are stored as a vector of bits
	  * indicating which side of the cut each customer is on.
	  \*-----------------------------------------------------------------*/
	 
       case SUBTOUR_ELIM_SIDE:
	 /*Here, I could just allocate enough memory up front and then
	   reallocate at the end istead of counting the number of entries in
	   the row first*/
	 coef = new_cut->coef;
	 for (i = 0; i<vrp->feas_sol_size; i++){
	    v0 = edges[feas_sol[i] << 1];
	    v1 = edges[(feas_sol[i] << 1) + 1];
	    if ((coef[v0 >> DELETE_POWER] & (1 << (v0 & DELETE_AND))) &&
		(coef[v1 >> DELETE_POWER] & (1 << (v1 & DELETE_AND)))){
	       lhs += 1;
	    }
	 }
	 new_cut->sense = 'L';
	 break;
	 
       case SUBTOUR_ELIM_ACROSS:
	 /*I could just allocate enough memory up front and then reallocate
	   at the end instead of counting the number of entries first*/
	 coef = new_cut->coef;
	 for (i = 0; i < vrp->feas_sol_size; i++){
	    v0 = edges[feas_sol[i] << 1];
	    v1 = edges[(feas_sol[i] << 1) + 1];
	    if ((coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1) ^
		(coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1)){
	       lhs += 1;
	    }
	 }
	 new_cut->sense = 'G';
	 break;
	 
       case CLIQUE:
	 coef = new_cut->coef;
	 size = (vertnum >> DELETE_POWER) + 1;
	 memcpy(&cliquecount, coef, ISIZE);
	 coef += ISIZE;
	 for (i = 0; i < vrp->feas_sol_size; i++){
	    v0 = edges[feas_sol[i] << 1];
	    v1 = edges[(feas_sol[i] << 1) + 1];
	    for (j = 0; j < cliquecount; j++){
	       clique_array = coef + size * j;
	       if ((clique_array[v0 >> DELETE_POWER] &
		    (1 << (v0 & DELETE_AND))) &&
		   (clique_array[v1 >> DELETE_POWER] &
		    (1 << (v1 & DELETE_AND)))){
		  lhs += 1;
	       }
	    }
	 }
	 break;
       /*__BEGIN_EXPERIMENTAL_SECTION__*/

       case FARKAS:
	 coef = new_cut->coef;
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
	 
	 for (fracs = 0, i = 0, lhs = 0; i < vrp->feas_sol_size; i++){
	    v0 = edges[feas_sol[i] << 1];
	    v1 = edges[(feas_sol[i] << 1) + 1];
	    edge_index = feas_sol[i];
	    if (isset(coef, v1) || isset(coef,v0)){
	       for (jj = 0; jj < num_arcs; jj++){
		  if (arcs[jj] == edge_index){
		     lhs += indicators[jj] ? -bigM : weights[fracs++];
		     break;
		  }
	       }
	       if (jj == num_arcs) lhs += bigM;
	    }
	 }
	 weights--;
	 FREE(arcs);
	 FREE(indicators);
	 FREE(weights);
	 break;
	 
       case NO_COLUMNS:
	 coef = new_cut->coef;
	 cpt = coef+ ((vertnum >> DELETE_POWER) + 1); 
	 memcpy((char *)&num_arcs, cpt, ISIZE);
	 cpt += ISIZE;
	 arcs = (int *) malloc(num_arcs * ISIZE);
	 indicators = (char *) malloc(num_arcs);
	 memcpy((char *)arcs, cpt, num_arcs * ISIZE);
	 cpt += num_arcs * ISIZE;
	 memcpy(indicators, cpt, num_arcs);
	 
	 for (i = 0, lhs = 0 ; i < vrp->feas_sol_size; i++){
	    v0 = vrp->edges[feas_sol[i] << 1];
	    v1 = vrp->edges[(feas_sol[i] << 1) + 1];
	    edge_index = feas_sol[i];
	    if (isset(coef, v1) || isset(coef,v0)){
	       for (jj = 0; jj < num_arcs; jj++){
		  if ( arcs[jj] == edge_index){
		     lhs += indicators[jj] ? 1.0 : 0.0;
		     break;
		  }
	       }
	       if (jj == num_arcs) lhs -= 1;
	    }
	 }
	 FREE(arcs);
	 FREE(indicators);
	 break;
	 
       case GENERAL_NONZEROS:
	 cpt = new_cut->coef;
	 memcpy((char *)&num_arcs, cpt, ISIZE);
	 cpt += ISIZE;
	 arcs = (int *) calloc(num_arcs, ISIZE);
	 weights = (double *) calloc(num_arcs, DSIZE);
	 memcpy((char *)arcs, cpt, num_arcs * ISIZE);
	 cpt += num_arcs * ISIZE;
	 memcpy((char *)weights, cpt, num_arcs * DSIZE);
	 
	 for (i = 0, lhs = 0; i < vrp->feas_sol_size; i++){
	    edge_index = feas_sol[i];
	    for (j = 0; j < num_arcs; j++){
	       if (arcs[j] == edge_index){
		  lhs += weights[j];
		  break;
	       }
	    }
	 }
	 FREE(arcs);
	 FREE(weights);
	 break;
       /*___END_EXPERIMENTAL_SECTION___*/
	 
       default:
	 printf("Unrecognized cut type!\n");
      }
      
      /*check to see if the cut is actually violated by the current solution --
	otherwise don't add it -- also check to see if its a duplicate*/
      if (new_cut->sense == 'G' ? lhs < new_cut->rhs : lhs > new_cut->rhs){
	 printf("CG: ERROR -- cut is violated by feasible solution!!!\n");
	 exit(1);
      }
   }
   
   return(USER_SUCCESS);
}
#endif

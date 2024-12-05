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

/* SYMPHONY include files */
#include "sym_macros.h"
#include "sym_constants.h"
#include "sym_proto.h"
#include "sym_cg.h"

/* VRP include files */
#include "vrp_cg.h"
#include "network.h"
extern "C"{
   #include "concorde.h"
}

int add_tsp_cuts PROTO((CCtsp_lpcut_in **tsp_cuts, int *cutnum, int vertnum,
			char tsp_prob, cut_data ***cuts, int *num_cuts,
			int *alloc_cuts));

/*===========================================================================*/

/*===========================================================================*\
 * This file contains the interface to the CONCORDE cutting plane routines
\*===========================================================================*/

/*===========================================================================*/

int tsp_cuts(network *n, int verbosity, char tsp_prob, int which_cuts,
	     cut_data ***cuts, int *num_cuts, int *alloc_cuts)
{
   edge *edges = n->edges;
   CCtsp_lpcut_in *tsp_cuts = NULL;
   int *tsp_edgelist = (int *) malloc(2*n->edgenum*ISIZE);
   double *tsp_x = (double *) malloc(n->edgenum*DSIZE);
   int i, cutnum = 0, cuts_added = 0, rval, seed;
   CCrandstate rstate;
   CCtsp_cutselect *sel;
   CCtsp_tighten_info *stats;
      
   stats = (CCtsp_tighten_info *) calloc(1, sizeof(CCtsp_tighten_info));
   sel = (CCtsp_cutselect *) calloc(1, sizeof(CCtsp_cutselect));

   if (tsp_prob){
      sel->connect          = 1;
      if (which_cuts & SUBTOUR){
	 sel->segments         = 1;
	 sel->exactsubtour     = 1;
      }
      if (which_cuts & BLOSSOM){
	 sel->fastblossom      = 1;
	 sel->ghfastblossom    = 1;
	 sel->exactblossom     = 0;
      }
      if (which_cuts & COMB){
	 sel->blockcombs       = 1;
	 sel->growcombs        = 0;
	 sel->prclique         = 0;
      }
   }else{
      if (which_cuts & BLOSSOM){
	 sel->fastblossom      = 1;
	 sel->ghfastblossom    = 1;
	 sel->exactblossom     = 1;
      }
   }
   
   for (i = 0; i < n->edgenum; i++, edges++){
      tsp_edgelist[i << 1] = edges->v0;
      tsp_edgelist[(i << 1) + 1] = edges->v1;
      tsp_x[i] = edges->weight;
   }

   if (sel->connect){
      rval = CCtsp_connect_cuts(&tsp_cuts, &cutnum, n->vertnum, n->edgenum,
				tsp_edgelist, tsp_x);
      if (rval) {
	 fprintf(stderr, "CCtsp_connect_cuts failed\n");
	 printf("CCtsp_connect_cuts failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d connect cuts\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i connect cuts added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
   }

   if (sel->segments){
      rval = CCtsp_segment_cuts(&tsp_cuts, &cutnum, n->vertnum, n->edgenum,
				tsp_edgelist, tsp_x);
      if (rval) {
	 fprintf(stderr, "CCtsp_segment_cuts failed\n");
	 printf("CCtsp_segment_cuts failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d segment cuts\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i segment cuts added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
    }

   if (sel->fastblossom){
      rval = CCtsp_fastblossom(&tsp_cuts, &cutnum, n->vertnum, n->edgenum,
			       tsp_edgelist, tsp_x);
      if (rval) {
	 fprintf(stderr, "CCtsp_fastblossom failed\n");
	 printf("CCtsp_fastblossom failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d fastblossom cuts\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i fastblossom cuts added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
   }

   if (sel->ghfastblossom){
      rval = CCtsp_ghfastblossom(&tsp_cuts, &cutnum, n->vertnum, n->edgenum,
				 tsp_edgelist, tsp_x);
      if (rval) {
	 fprintf(stderr, "CCtsp_ghfastblossom failed\n");
	 printf("CCtsp_ghfastblossom failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d ghfastblossom cuts\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i ghfastblossom cuts added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
   }

   if (sel->blockcombs){
      rval = CCtsp_block_combs(&tsp_cuts, &cutnum, n->vertnum, n->edgenum,
			       tsp_edgelist, tsp_x, TRUE);
      if (rval) {
	 fprintf(stderr, "CCtsp_block_combs failed\n");
	 printf("CCtsp_block_combs failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d block combs\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i block combs added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
   }

   if (sel->growcombs){
      rval = CCtsp_edge_comb_grower(&tsp_cuts, &cutnum, n->vertnum,
				    n->edgenum, tsp_edgelist, tsp_x, stats);
      if (rval) {
	 fprintf(stderr, "CCtsp_edge_comb_grower failed\n");
	 printf("CCtsp_edge_comb_grower failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d grown combs\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i grown combs added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
   }

   if (sel->prclique){
      rval = CCtsp_pr_cliquetree(&tsp_cuts, &cutnum, n->vertnum,
				 n->edgenum, tsp_edgelist, tsp_x, stats);
      if (rval) {
	 fprintf(stderr, "CCtsp_pr_cliquetree failed\n");
	 printf("CCtsp_pr_cliquetree failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d PR cliquetrees\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i PR cliquetrees added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
   }

   if (sel->exactsubtour){
      rval = CCtsp_exact_subtours(&tsp_cuts, &cutnum, n->vertnum,
				  n->edgenum, tsp_edgelist, tsp_x);
      if (rval) {
	 fprintf(stderr, "CCtsp_exact_subtours failed\n");
	 printf("CCtsp_exact_subtours failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d exact subtours\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i exactsubtours added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
   }

   if (sel->exactblossom){
      seed = (int) CCutil_real_zeit ();
      CCutil_sprand(seed, &rstate);
      rval = CCtsp_exactblossom(&tsp_cuts, &cutnum, n->vertnum, n->edgenum,
				tsp_edgelist, tsp_x, &rstate);
      if (rval) {
	 fprintf(stderr, "CCtsp_exactblossom failed\n");
	 printf("CCtsp_exactblossom failed\n");
	 rval = 1;
      }
      if (verbosity > 3)
	 printf("Found %2d exactblossoms\n", cutnum);
      if (!rval && cutnum > 0){
	 cuts_added += add_tsp_cuts(&tsp_cuts, &cutnum, n->vertnum, tsp_prob,
				    cuts, num_cuts, alloc_cuts);
	 if (cuts_added){
	    if (verbosity > 3)
	       printf("%i exact blossoms added\n", cuts_added);
	    goto CLEANUP;
	 }
      }
   }

CLEANUP:

   FREE(stats);
   FREE(tsp_edgelist);
   FREE(tsp_x);
   
   return(cuts_added);
}

/*===========================================================================*/

int add_tsp_cuts(CCtsp_lpcut_in **tsp_cuts, int *cutnum, int vertnum,
		 char tsp_prob, cut_data ***cuts, int *num_cuts,
		 int *alloc_cuts)
{
   cut_data cut;
   int i, j, k, cliquecount, cuts_added = 0;
   char *coef, *clique_array;
   char valid = TRUE;
   int size = (vertnum >> DELETE_POWER) + 1;
   CCtsp_lpcut_in *tsp_cut, *tsp_cut_next;   

   if (*cutnum <= 0) return(0);
   
   cut.type = CLIQUE;
   cut.name = CUT__SEND_TO_CP;
   cut.range = 0;
   cut.branch = ALLOWED_TO_BRANCH_ON;
   for (tsp_cut = *tsp_cuts; tsp_cut; tsp_cut = tsp_cut->next){
      cliquecount = tsp_cut->cliquecount;
      cut.sense = 'L';
      cut.rhs = (cliquecount == 1 ? 0.0 : -((double)cliquecount)/2.0 + 1.0);
      cut.size = ISIZE + cliquecount * size;
      cut.coef = coef = (char *) calloc(cut.size, sizeof(char));
      memcpy(cut.coef, (char *) (&cliquecount), ISIZE);
      clique_array = cut.coef + ISIZE;
      for (i = 0; i < cliquecount; i++, clique_array += size){
	 valid = TRUE;
	 for(j = 0; j < tsp_cut->cliques[i].segcount; j++){
	    for(k = tsp_cut->cliques[i].nodes[j].lo;
		k <= tsp_cut->cliques[i].nodes[j].hi; k++){
	       cut.rhs++;
	       if (!k && !tsp_prob){
		  valid = FALSE;
		  break;
	       }
	       clique_array[k >> DELETE_POWER] |= (1 << (k & DELETE_AND));
	    }
	    /*For each tooth, we want to add |T|-1 to the rhs so we have to
	      subtract off the one here. It subtracts one for the handle too
	      but that is compensated for above*/
	    if (!valid) break;
	 }
	 cut.rhs--;
	 if (!valid) break;
      }
      if (!valid){
	 FREE(cut.coef);
	 continue;
      }

      cg_send_cut(&cut, num_cuts, alloc_cuts, cuts);
      cuts_added++;

      FREE(cut.coef);
   }

   for (tsp_cut = *tsp_cuts; tsp_cut; tsp_cut = tsp_cut_next){
      tsp_cut_next = tsp_cut->next;
      CCtsp_free_lpcut_in(tsp_cut);
      FREE(tsp_cut);
   }
   *tsp_cuts = NULL;
   *cutnum = 0;
   
   return(cuts_added);
}


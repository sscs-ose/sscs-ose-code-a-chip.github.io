#include <math.h>
#include <stdlib.h>

#include "qsortucb.h"
#include "BB_constants.h"
#include "sym_timemeas.h"
#include "sym_messages.h"
#include "decomp.h"
#include "decomp_user.h"
#include "compute_cost.h"
#include "network.h"
#include "decomp_types.h"
#include "sym_dg_params.h"
#include "vrp_sym_dg.h"
#include "vrp_macros.h"
#include "vrp_const.h"
#include "ind_sort.h"

int int_compar(const void *int1, const void *int2)
{
   return((*((int *)int1)) - (*((int *)int2)));
}

/*===========================================================================*/

dcmp_col_set *user_generate_new_cols(cg_prob *p)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)(p->user);
   int size = vrp->vertnum+vrp->numroutes-1;
   dcmp_col_set *cols = (dcmp_col_set *) calloc (1, sizeof(dcmp_col_set));
   int *intour;
   int *tour;
   edge **stack;
   vertex *verts;
   elist *cur_edge;
   int position = 0;
   int numroutes = vrp->numroutes;
   
   cols->lb = (double *) calloc (COL_BLOCK_SIZE, sizeof(double));
   cols->ub = (double *) calloc (COL_BLOCK_SIZE, sizeof(double));
   cols->obj = (double *) calloc (COL_BLOCK_SIZE, sizeof(double));
   cols->matbeg = (int *) calloc (COL_BLOCK_SIZE+1, sizeof(int));
   cols->matind = (int *) calloc (size*COL_BLOCK_SIZE, sizeof(int));
   cols->matval = (double *) calloc (size*COL_BLOCK_SIZE, sizeof(double));
   cols->num_cols = 0;
   cols->max_cols = COL_BLOCK_SIZE;
   cols->nzcnt = 0;
   cols->max_nzcnt = size*COL_BLOCK_SIZE;
   
   intour = (int *) calloc (vrp->vertnum, sizeof(int));
   tour = (int *) calloc (size+1, sizeof(int));
   
   if (!vrp->n){
      ind_sort(p->cur_sol.xind, p->cur_sol.xval, p->cur_sol.xlength);
      vrp->n = createnet(p->cur_sol.xind, p->cur_sol.xval, p->cur_sol.xlength,
			 p->cur_sol.lpetol, vrp->edges, vrp->demand,
			 vrp->vertnum);
   }
   
   verts = vrp->n->verts;
   
   cur_edge = verts[0].first;
   stack=(edge **) malloc(verts[0].degree*sizeof(edge *));
   
   p->dcmp_data.timeout = time(NULL);
   
   while(cur_edge &&cur_edge->data->weight == 2){
      intour[cur_edge->other_end]++;
      tour[intour[0]++] = cur_edge->other_end+numroutes;
      tour[cur_edge->other_end+numroutes]=intour[0];
      cur_edge->data->deleted = TRUE;
      stack[position++]=cur_edge->data;
      cur_edge = cur_edge->next_edge;
   }
   if (cur_edge){
      bfm(p, 0, intour, tour, cols, stack, position);
   }else{
      add_tour_to_col_set(p, tour, vrp, cols);
   }      
   
   FREE(tour);
   FREE(intour);
   FREE(stack);
   
   return(cols);
}

/*===========================================================================*/

char bfm(cg_prob *p, int cur_node, int *intour, int *tour, dcmp_col_set *cols,
	 edge **stack, int position)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)(p->user);
   int numroutes = vrp->numroutes, vertnum = vrp->vertnum;
   vertex *verts = vrp->n->verts;
   int i;
   int count=0;
   elist *cur_edge;
   
   if (cur_node == 0 && intour[0] == numroutes){
      for (i = 0; i < vertnum; i++){
	 if (intour[i] == FALSE)
	    break;
      }
      if (i < vertnum){
	 return(TRUE);
      }
      add_tour_to_col_set(p, tour, vrp, cols);
      if (time(NULL) - p->dcmp_data.timeout > p->par.decomp_timeout ||
	  cols->num_cols == p->par.decomp_max_col_num_per_iter){
	 return(FALSE);
      }else{
	 return(TRUE);
      }
   }
   
   intour[cur_node]++;
   
   if ( cur_node ){
      for (cur_edge = verts[cur_node].first; cur_edge;
	   cur_edge = cur_edge->next_edge){
	 if (cur_edge->data->weight == 1){
	    if (cur_edge->other_end && !intour[cur_edge->other_end]){
	       tour[cur_node+numroutes] = cur_edge->other_end+numroutes;
	       if (time(NULL) - p->dcmp_data.timeout > p->par.decomp_timeout ||
		   !bfm(p, cur_edge->other_end, intour, tour, cols, stack,
			position)){
		  return(FALSE);
	       }else{
		  intour[cur_node]--;
		  return(TRUE);
	       }
	    }
	 }else{
	    break;
	 }
      }
	
      for (cur_edge = verts[cur_node].first; cur_edge;
	   cur_edge = cur_edge->next_edge){
         if (!(cur_edge->other_end?
	       intour[cur_edge->other_end] : cur_edge->data->deleted)){
	    tour[cur_node+numroutes] = cur_edge->other_end?
	       cur_edge->other_end+numroutes:intour[0];
	    if (time(NULL) - p->dcmp_data.timeout > p->par.decomp_timeout ||
		!bfm(p, cur_edge->other_end, intour, tour, cols, stack,
		     position))
	       return(FALSE);
	 }
      }
   }else{
      for (cur_edge = verts[cur_node].first; cur_edge;
	   cur_edge = cur_edge->next_edge)
	 if (!(intour[cur_edge->other_end]) && !(cur_edge->data->deleted)){
	    tour[intour[0]-1] = cur_edge->other_end+numroutes;
	    if (!vrp->par.allow_one_routes_in_bfm)
		cur_edge->data->deleted = TRUE;
	    if (time(NULL) - p->dcmp_data.timeout > p->par.decomp_timeout ||
		!bfm(p, cur_edge->other_end, intour, tour, cols, stack,
		     position))
	       return(FALSE);
	    cur_edge->data->deleted = TRUE;
	    stack[position++]=cur_edge->data;
	    count++;
	 }
      for ( i=0;i<count; i++){
	 (stack[--position])->deleted = FALSE;
      }
   } 
   intour[cur_node]--;
   return(TRUE);
   
}

/*===========================================================================*/

void add_tour_to_col_set(cg_prob *p, int *tour, cg_vrp_spec *vrp,
			 dcmp_col_set *cols)
{
   int *coef = cols->matind+cols->nzcnt;
   int size = vrp->vertnum+vrp->numroutes-1, k;
   int cur_node, next_node;
   double cost, *unbdd_row = p->dcmp_data.unbdd_row;
   int dunbr = p->dcmp_data.dunbr;
   double gamma = unbdd_row[p->dcmp_data.lp_data->m-1];
   double etol = p->cur_sol.lpetol;
   int numroutes = vrp->numroutes;
   char name[100];
   
   if (cols->num_cols == cols->max_cols){
      cols->max_cols += COL_BLOCK_SIZE;
      cols->lb = (double *) realloc ((char *)cols->lb,
				      (cols->max_cols)*sizeof(double));
      cols->ub = (double *) realloc ((char *)cols->ub,
				      (cols->max_cols)*sizeof(double));
      cols->obj = (double *) realloc ((char *)cols->obj,
				      (cols->max_cols)*sizeof(double));
      cols->matbeg = (int *) realloc ((char *)cols->matbeg,
				      (cols->max_cols+1)*sizeof(int));
   }
   if (cols->nzcnt + size > cols->max_nzcnt){
      cols->max_nzcnt += size*COL_BLOCK_SIZE;
      cols->matind = (int *) realloc ((char *)cols->matind,
				      cols->max_nzcnt*sizeof(int));
      cols->matval = (double *) realloc ((char *)cols->matval,
					 cols->max_nzcnt*sizeof(double));
   }

   coef = cols->matind + cols->nzcnt;

   coef[0] = INDEX(0, tour[0]-numroutes);
   cost = dunbr ? unbdd_row[coef[0]]:0;
   for (cur_node = tour[0], next_node = tour[cur_node], k = 1;;
	cur_node = next_node, next_node = tour[cur_node]){
      if (next_node == numroutes){
	 coef[k] = INDEX(0, (cur_node-numroutes));
	 cost += dunbr ? unbdd_row[coef[k]] : 0;
	 break;
      }
      coef[k] = INDEX((cur_node>numroutes?cur_node-numroutes:0),
		      (next_node>numroutes?next_node-numroutes:0));
      cost += dunbr ? unbdd_row[coef[k]] : 0;
      k++;
   }

   if (vrp->dg_id && p->par.verbosity > 4){
      sprintf(name, "Partial Decomp Tour (%i,%i,%i,%i)",
	      p->cur_sol.xlevel, p->cur_sol.xiter_num, p->cur_sol.xiter_num,
	      cols->num_cols);
      display_part_tour(vrp->dg_id, TRUE, name, tour, numroutes,
			CTOI_WAIT_FOR_CLICK_AND_REPORT);
   }
   
   if (dunbr && cost + gamma >= -etol)
      return;

   qsort ((char *)coef, size, sizeof(int), int_compar);

   cols->nzcnt += size;
   cols->matbeg[cols->num_cols+1] = cols->matbeg[cols->num_cols]+size;
   cols->num_cols++;
}

/*===========================================================================*/

void user_unpack_col(cg_prob *p, col_data *col, int *nzcnt, int *matind)
{
   memcpy ((char *) matind, col->coef, col->size);
}

/*===========================================================================*/

void user_display_col(cg_prob *p, col_data *col)
{
   int nzcnt = col->size/(sizeof(int));
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   int i, *origind = (int *) calloc ((int)nzcnt, sizeof(int));
   double *x = (double *) calloc ((int)nzcnt, sizeof(double));
   
   for (i=0; i<nzcnt; i++){
      origind[i] = (int)(((int *)col->coef)[i]);
      x[i] = 1;
   }

   draw_weighted_edge_set(vrp->dg_id, (char *)"Decomp Column", nzcnt, origind,
			  x, p->cur_sol.lpetol);
}

/*===========================================================================*/

int user_check_col(cg_prob *p, int *colind, double *colval, int collen)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)p->user;
   int capacity = vrp->capacity, *demand = vrp->demand;
   int weight, num_cuts = 0;
   int cut_size = (vrp->vertnum >> DELETE_POWER) +1;
   network *n;
   elist *cur_route_start;
   vertex *verts;
   int cur_route, cur_vert, prev_vert, cust_num;
   edge *edge_data;
   cut_data *new_cut;

   n = createnet(colind, colval, collen-1, p->cur_sol.lpetol,
		 vrp->edges, vrp->demand, vrp->vertnum);

   verts = n->verts;
   new_cut = (cut_data *) calloc (1, sizeof(cut_data));
   new_cut->size = cut_size;
   /*new_cut->level = p->cur_sol.xlevel;*/
   
   for (cur_route_start = verts[0].first, cur_route = 0,
	edge_data = cur_route_start->data; cur_route < vrp->numroutes;
	cur_route++){
      edge_data = cur_route_start->data;
      edge_data->scanned = TRUE;
      cur_vert = edge_data->v1;
      prev_vert = weight = cust_num = 0;
      
      new_cut->coef = (char *) calloc (cut_size, sizeof(char));

      while (cur_vert){
	 /*keep tracing around the route and whenever the addition
	   of the next customer causes a violation, impose the
	   constraint induced
	   by the set of customers seen so far on the route*/
	 new_cut->coef[cur_vert >> DELETE_POWER] |=
	    (1 << (cur_vert & DELETE_AND));
	 cust_num++;
	 if ((weight += demand[cur_vert]) > capacity){
	    new_cut->type = (cust_num < vrp->vertnum/2 ?
			   SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	    new_cut->rhs = (new_cut->type ==SUBTOUR_ELIM_SIDE ?
			    RHS(cust_num, weight, capacity):
			    2*BINS(weight, capacity));
	    if (check_cut(p, vrp, new_cut))
	       num_cuts += cg_send_cut(new_cut);
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
      }
      edge_data->scanned = TRUE;
      
      free ((char *) new_cut->coef);
      
      while (cur_route_start->data->scanned){/*find the next edge leading out
					       of the depot which has not yet
					       been traversed to start the next
					       route*/
	 if (!(cur_route_start = cur_route_start->next_edge)) break;
      }
   }
   for (cur_route_start = verts[0].first; cur_route_start;
	cur_route_start = cur_route_start->next_edge)
      cur_route_start->data->scanned = FALSE;

   free_net(n);
   FREE(new_cut);
   
   return(num_cuts);
}

/*===========================================================================*/

char check_cut(cg_prob *p, cg_vrp_spec *vrp, cut_data *cut)
{
   network *n = vrp->n;
   char *coef;
   int v0, v1;
   vertex *verts;
   int vertnum;
   double lhs = 0;
   elist *cur_edge;
   int i;

   verts = n->verts;
   vertnum = n->vertnum;
   
   /*----------------------------------------------------------------------*\
   | Here the cut is "unpacked" and checked for violation. Each cut is      |
   | stored as compactly as possible. The subtour elimination constraints   |
   | are stored as a vector of bits indicating which side of the cut each   |
   | node is on. If the cut is violated, it is sent back to the lp.         |
   | Otherwise, "touches" is incremented. "Touches" is a measure of the     |
   | effectiveness of a cut and indicates how long it has been since a      |
   | cut was useful                                                         |
   \*----------------------------------------------------------------------*/
   switch (cut->type){
    
    case SUBTOUR_ELIM_SIDE:
      coef = cut->coef;
      for (lhs = 0, v0 = 0; v0<vertnum; v0++){
	 if (!(coef[v0 >> DELETE_POWER] & (1 << (v0 & DELETE_AND))))
	    continue;
	 for(cur_edge = verts[v0].first;cur_edge;cur_edge=cur_edge->next_edge){
	    v1 = cur_edge->other_end;
	    if (coef[v1 >> DELETE_POWER] & (1 << (v1 & DELETE_AND)))
	       lhs += cur_edge->data->weight;
	 }
      }
      return (lhs/2 > (double)(cut->rhs)+p->cur_sol.lpetol);

    case SUBTOUR_ELIM_ACROSS:
      coef = cut->coef;
      for (lhs = 0, i = 0; i<p->cur_sol.xlength; i++){
	 v0 = vrp->edges[p->cur_sol.xind[i] << 1];
	 v1 = vrp->edges[(p->cur_sol.xind[i] << 1) + 1];
	 if ((coef[v0 >> DELETE_POWER] >> (v0 & DELETE_AND) & 1) ^
	     (coef[v1 >> DELETE_POWER] >> (v1 & DELETE_AND) & 1))
	    lhs += p->cur_sol.xval[i];
      }
      return (lhs < (double)(cut->rhs)-p->cur_sol.lpetol);

    default:
      printf("Cut types not recognized! \n\n");
      return(FALSE);
   }

   return(FALSE);
}

/*========================================================================*/

void user_pack_col(int *colind, int collen, col_data *col)
{
   col->size = collen*sizeof(int);
   col->coef = (char *) calloc (col->size, sizeof(char));
   memcpy(col->coef, colind, col->size);
}

/*========================================================================*/

void user_free_decomp_data_structures(cg_prob *p, void **user)
{
   cg_vrp_spec *vrp = (cg_vrp_spec *)(*user);

   free_net(vrp->n);

   vrp->n = NULL;
}

/*===========================================================================*/

char user_set_rhs(int varnum, double *rhs, int length, int *ind,
		  double *val, void *user)
{
   return(FALSE);
}










/*===========================================================================*/
/*                                                                           */
/* This file is part of a demonstration application for use with the         */
/* SYMPHONY Branch, Cut, and Price Library. This application is a solver for */
/* the Vehicle Routing Problem and the Traveling Salesman Problem.           */
/*                                                                           */
/* This application was developed by Ted Ralphs (ted@lehigh.edu)             */
/*                                                                           */
/* This file was jointly authored by Ted Ralphs and Leonid Kopman.           */
/*                                                                           */
/* (c) Copyright 2000-2007 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

/* system include files */
#include <stdlib.h>
#include <math.h>
#include <string.h>           /* memset() is defined here in LINUX */

/* SYMPHONY include files */
#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_messages.h"
#include "sym_proccomm.h"
#include "sym_cg.h"

/* VRP include files */
#include "vrp_cg.h"
#include "vrp_macros.h"
#include "network.h"

/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
#include "util.h"
extern CCrandstate rand_state;
#endif
/*___END_EXPERIMENTAL_SECTION___*/

/*===========================================================================*/

/*===========================================================================*\
 * This file implements the greedy shrinking algorithm of Augerat, et al.
 * The implementation was done by Leonid Kopman.
\*===========================================================================*/

void reduce_graph(network *n, double etol, int *demand)
{
   elist *e1, *e2, *e3;
   edge *cur_edge;
   int v1, v2, deg, count, i, k;
   edge *edges = n->edges;
   int num_edges = n->edgenum;
   int edges_deleted = 0;
   vertex *verts = n->verts;
   vertex *v2_pt, *third_node;
   
   while(TRUE){
      num_edges = n->edgenum;
      edges_deleted = 0;
      for (i = 0; i < num_edges; i++){
	 cur_edge = edges + i;
	 if (cur_edge->weight >= 1 - etol && cur_edge->v0 &&
	     cur_edge->v1 && !(cur_edge->deleted)){
	    cur_edge->deleted = TRUE;
	    n->edgenum--;
	    edges_deleted++;
	    v1 = (verts[cur_edge->v0].degree ==
		  MIN(verts[cur_edge->v0].degree, verts[cur_edge->v1].degree))?
	          cur_edge->v0 : cur_edge->v1;
	    v2 = (v1 == cur_edge->v0) ? cur_edge->v1 : cur_edge->v0;
	    verts[v1].deleted = TRUE;
	    demand[v2] += demand[v1];
	    demand[v1] = 0;
	    v2_pt = verts + v2;
	    v2_pt->degree--;
	    if (v2_pt->first->other_end == v1){
	       v2_pt->first = v2_pt->first->next_edge;
	    }else{
	       for (e3 = v2_pt->first; e3 && e3->next_edge; e3 = e3->next_edge)
		  if (e3->next_edge->other_end == v1){
		     e3->next_edge = e3->next_edge->next_edge;
		     if (e3->next_edge == NULL) v2_pt->last = e3;
		     break;
		  }
	    }
	    
	    if (!(v2_pt->orig_node_list_size))
	       v2_pt->orig_node_list = (int *) malloc(n->vertnum*ISIZE);
	    (v2_pt->orig_node_list)[(v2_pt->orig_node_list_size)++] = v1;
	    
	    for (k = 0; k < verts[v1].orig_node_list_size; k++){
	       (v2_pt->orig_node_list)[(v2_pt->orig_node_list_size)++] =
		  (verts[v1].orig_node_list)[k];
	    }
	    deg = verts[v1].degree;
	    
	    for (e1 = verts[v1].first, count=0; e1 && (count < deg); count++ ){
	       third_node = e1->other;
	       if (third_node->orignodenum == v2){
		  e1 = e1->next_edge;
		  continue;
	       }
	       for (e2 = v2_pt->first; e2; e2 = e2->next_edge){
		  if (e2->other_end == e1->other_end ){
		     e2->data->weight += e1->data->weight;
		     e1->data->deleted = TRUE;
		     edges_deleted++;
		     (third_node->degree)--;
		     if (third_node->first->other_end == v1){
			third_node->first=third_node->first->next_edge;
		     }else{
			for (e3 = third_node->first; e3 && e3->next_edge;
			     e3 = e3->next_edge)
			   if (e3->next_edge->other_end == v1){
			      e3->next_edge = e3->next_edge->next_edge;
			      if (e3->next_edge == NULL) third_node->last = e3;
			      break;
			   }
		     }
		     break;
		  }
	       }
	       if (e2){
		  e1 = e1->next_edge;
		  continue;
	       }
	       /* ok, so e1->other_node is not incident to v2 */
	       for (e3 = third_node->first; e3 ; e3 = e3->next_edge){
		  if (e3->other_end == v1){
		     e3->other = v2_pt;
		     e3->other_end = v2;
		     e3->data->v0 = MIN(v2, third_node->orignodenum);
		     e3->data->v1 = MAX(v2, third_node->orignodenum);
		     break;
		  }
	       }
	       v2_pt->last->next_edge = e1;
	       v2_pt->last = e1;
	       v2_pt->degree++;
	       e1=e1->next_edge;
	       v2_pt->last->next_edge = NULL;
	    }
	 }
      }
      if (!edges_deleted) break;
   }
}

/*===========================================================================*/

int greedy_shrinking1(network *n, double truck_cap, double etol,
		      int max_shrink_cuts, cut_data *new_cut,
		      int *compnodes, int *compmembers, int compnum,
		      char *in_set, double *cut_val, int *ref, char *cut_list,
		      int *demand, cut_data ***cuts, int *num_cuts,
		      int *alloc_cuts)
{
   double set_cut_val, set_demand;
   vertex *verts = n->verts;
   elist *e;
   int shrink_cuts = 0, i, j, k;
   char *pt, *cutpt;
   int *ipt; 
   double  *dpt;
   int vertnum = n->vertnum;
  
   int max_vert = 0, set_size, begin = 1, cur_comp, end = 1, other_end;
   char *coef;
   double maxval, weight;
   vertex *cur_nodept;
   
   new_cut->size = (vertnum >> DELETE_POWER) + 1;
   new_cut->coef = coef = (char *) (calloc(new_cut->size, sizeof(char)));
   memset(cut_list, 0, new_cut->size * (max_shrink_cuts + 1));
   
   *in_set = 0;
   
   for (i = 1; i < vertnum;  i++){
      if (verts[compmembers[i]].deleted) compmembers[i] = 0;
      ref[compmembers[i]] = i;
   }
   *ref = 0;
   /* ref is a reference array for compmembers: gives a place
      in which a vertex is listed in  compmembers */
   
   for (cur_comp = 1; cur_comp <= compnum;
	begin += compnodes[cur_comp], cur_comp++)  /* for every component */
      for (i = begin, end = begin + compnodes[cur_comp]; i < end; i++){
	 if (compmembers[i] == 0) continue;
	 /* for every node as a starting one */
	 /*initialize the data structures */
	 memset(in_set  + begin, 0, compnodes[cur_comp] * sizeof(char));
	 memset(cut_val + begin, 0, compnodes[cur_comp] * sizeof(double));
	 in_set[i] = 1;
	 set_size = 1 + verts[compmembers[i]].orig_node_list_size; 
	 set_cut_val = 0;     
	 for (e = verts[compmembers[i]].first; e; e = e->next_edge){
	    if (e->other_end)
	       cut_val[ref[e->other_end]] = e->data->weight;
	    set_cut_val += e->data->weight;
	 }
	 set_demand = demand[compmembers[i]];  
	 
	 while(TRUE){ 
	    if (set_cut_val < 2*(ceil(set_demand/truck_cap)) - etol &&
		set_size > 2){
	       memset(coef, 0, new_cut->size*sizeof(char));
	       for (j = begin, ipt = compmembers + begin; j < end; j++, ipt++){
		  if (in_set[j]){
		     cur_nodept = verts + (*ipt);
		     if (cur_nodept->orig_node_list_size)
			for (k = 0; k < cur_nodept->orig_node_list_size; k++)
			   (coef[(cur_nodept->orig_node_list)[k] >>
				DELETE_POWER]) |=
			      (1 << ((cur_nodept->orig_node_list)[k] &
				     DELETE_AND));
		     (coef[(*ipt) >> DELETE_POWER]) |=
			(1 << ((*ipt) & DELETE_AND));
		  }  
	       }
	       new_cut->type = (set_size < vertnum/2 ?
				SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	       new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
				RHS((int)set_size,(int)set_demand,
				    (int)truck_cap):
				2*BINS((int)set_demand, (int)truck_cap));
	       for (k = 0, cutpt = cut_list; k < shrink_cuts; k++,
		       cutpt += new_cut->size)
		  if (!memcmp(coef, cutpt, new_cut->size*sizeof(char)))
		     break;/* same cuts */ 
	       if (k >= shrink_cuts){ 
		  shrink_cuts +=
		     cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
		  memcpy(cutpt, coef, new_cut->size);
	       }
	       if (shrink_cuts > max_shrink_cuts){
		  FREE(new_cut->coef);
		  return(shrink_cuts);
	       }
	    } 
	    for (maxval = -1, pt = in_set + begin, dpt = cut_val + begin,
		    j = begin; j < end; pt++, dpt++, j++){
	       if (!(*pt) && *dpt > maxval){
		  maxval = cut_val[j];
		  max_vert = j; 
	       }
	    }
	    if (maxval > 0){    /* add the vertex to the set */
	       in_set[max_vert]=1;
	       set_size += 1+ verts[compmembers[max_vert]].orig_node_list_size;
	       set_demand += demand[compmembers[max_vert]];
	       cut_val[max_vert] = 0;
	       for (e=verts[compmembers[max_vert]].first; e; e = e->next_edge){
		  other_end = ref[e->other_end];
		  weight = e->data->weight;
		  set_cut_val += (in_set[other_end]) ? (-weight):weight;
		  cut_val[other_end] += (in_set[other_end]) ? 0 : weight;
		  
	       }
	    }
	    else{ /* can't add anything to the set */
	       break;
	    }
	 }   
      }
   FREE(new_cut->coef);
   return(shrink_cuts);
}

/*===========================================================================*/

int greedy_shrinking6(network *n, double truck_cap, double etol,
		      cut_data *new_cut, int *compnodes,
		      int *compmembers, int compnum,char *in_set,
		      double *cut_val, int *ref, char *cut_list,
		      int max_shrink_cuts, int *demand, int trial_num,
		      double prob, cut_data ***cuts, int *num_cuts,
		      int *alloc_cuts)
{
   double set_cut_val, set_demand;
   vertex  *verts = n->verts;
   elist *e;
   int i, j, k, shrink_cuts = 0;
   char *pt, *cutpt;
   double *dpt;
   int vertnum = n->vertnum;
  
   int max_vert = 0, set_size, begin = 1, cur_comp, end = 1, num_trials;
   char *coef;
   double maxval;
   double denominator=pow(2.0,31.0)-1.0;
   double r, q;
   
   int other_end;
   double weight;
   int *ipt; 
   vertex *cur_nodept;
  
   new_cut->size = (vertnum >> DELETE_POWER) + 1;
   new_cut->coef =coef= (char *) (calloc(new_cut->size,sizeof(char)));
   memset(cut_list, 0, new_cut->size * (max_shrink_cuts +1));
   
   
   *in_set=0;
   
   for(i = 1; i < vertnum; i++){
      if (verts[compmembers[i]].deleted) compmembers[i] = 0;
      ref[compmembers[i]] = i;
   }
   *ref = 0;  
   
   /* ref is a reference array for compmembers: gives a place
      in which a vertex is listed in  compmembers */
   
   for (cur_comp = 1; cur_comp <= compnum; begin += compnodes[cur_comp],
	   cur_comp++){
      /* for every component */
      if (compnodes[cur_comp] <= 7) continue;
      
      for (num_trials = 0; num_trials < trial_num * compnodes[cur_comp];
	num_trials++){
	 end = begin + compnodes[cur_comp];
	 /*initialize the data structures */
	 memset(in_set + begin, 0, compnodes[cur_comp] * sizeof(char));
	 memset(cut_val+ begin, 0, compnodes[cur_comp] * sizeof(double));
	 
	 set_cut_val = 0;
	 set_size = 0;
	 set_demand = 0;
         for (i = begin; i < end; i++ ){
	    if (compmembers[i] == 0) continue;
/*__BEGIN_EXPERIMENTAL_SECTION__*/
#if 0
	    r  = CCutil_lprand(&rand_state)/CC_PRANDMAX;
#endif
/*___END_EXPERIMENTAL_SECTION___*/
	    r = (RANDOM()/denominator);
	    q = (prob/compnodes[cur_comp]);
	    if (r < q){
	       in_set[i] = 1;
	       set_size += 1 + verts[compmembers[i]].orig_node_list_size;
	       set_demand += demand[compmembers[i]];
	       for (e = verts[compmembers[i]].first; e; e = e-> next_edge){
		  other_end = ref[e->other_end];
		  weight = e->data->weight;
		  set_cut_val += (in_set[other_end]) ? (-weight) : weight;
		  cut_val[other_end] += (in_set[other_end]) ? 0 : weight;
	       }
	    }
	 }
	 while(set_size){ 
	    if (set_cut_val < 2*(ceil(set_demand/truck_cap)) - etol &&
		set_size > 2){
	       memset(coef, 0, new_cut->size*sizeof(char));
	       for (j = begin, ipt = compmembers + begin; j < end; j++, ipt++)
		  if (in_set[j]){
		     cur_nodept = verts + (*ipt);
		     if (cur_nodept->orig_node_list_size)
			for (k = 0; k < cur_nodept->orig_node_list_size; k++)
			   (coef[(cur_nodept->orig_node_list)[k] >>
				DELETE_POWER]) |=
			      (1 << ((cur_nodept->orig_node_list)[k] &
				     DELETE_AND));
		     (coef[(*ipt) >> DELETE_POWER]) |= (1 << ((*ipt) &
							      DELETE_AND));
		  }  
	       new_cut->type = (set_size < vertnum/2 ?
				SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	       new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
			       RHS((int)set_size,(int)set_demand,(int)truck_cap):
			       2*BINS((int)set_demand, (int)truck_cap));
	       for (k = 0, cutpt = cut_list; k < shrink_cuts; k++,
		       cutpt += new_cut->size)
		  if (!memcmp(coef, cutpt, new_cut->size*sizeof(char))) break; 
	       if ( k >= shrink_cuts){
		  shrink_cuts +=
		     cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
		  memcpy(cutpt, coef, new_cut->size);
	       }
	 
	       if ( shrink_cuts > max_shrink_cuts){
		  FREE(new_cut->coef);
		  return(shrink_cuts);
	       }
	    } 
	    for (maxval = -1, pt = in_set+begin, dpt = cut_val+begin,
		    j = begin; j < end; pt++, dpt++, j++){
	       if (!(*pt) && *dpt > maxval){
		  maxval = cut_val[j];
		  max_vert = j; 
	       }
	    }
	    if (maxval > 0){    /* add the vertex to the set */
	       in_set[max_vert]=1;
	       set_size+=1+ verts[compmembers[max_vert]].orig_node_list_size;
	       set_demand+=demand[compmembers[max_vert]];
	       cut_val[max_vert]=0;
	       for (e = verts[compmembers[max_vert]].first; e;
		    e = e->next_edge){
		  other_end = ref[e->other_end];
		  weight = e->data->weight;
		  set_cut_val += (in_set[other_end]) ? (-weight) : weight;
		  cut_val[other_end]+=(in_set[other_end]) ? 0 : weight;
	       }
	    }
	    else{ /* can't add anything to the set */
	       break;
	    }
	 }   
      }
   }
   
   FREE(new_cut->coef);
   return(shrink_cuts);
}

/*===========================================================================*/

int greedy_shrinking1_one(network *n, double truck_cap, double etol,
			  int max_shrink_cuts, cut_data *new_cut,char *in_set,
			  double *cut_val, char *cut_list, int num_routes,
			  int *demand, cut_data ***cuts, int *num_cuts,
			  int *alloc_cuts)
{
 
   double set_cut_val, set_demand;
   vertex  *verts = n->verts;
   elist *e;
   int i, j, k, shrink_cuts = 0;
   char *pt, *cutpt;
   double  *dpt;
   int vertnum = n->vertnum;
   int max_vert = 0;
   int set_size;
   /* int flag=0; */

   double complement_demand, total_demand = verts[0].demand; 
   double complement_cut_val; 
   int complement_size; 
   char *coef;
   double maxval;
   int other_end;
   double weight; 
   vertex *cur_nodept;
   
   new_cut->size = (vertnum >> DELETE_POWER) + 1;
   new_cut->coef = coef = (char *) (calloc(new_cut->size,sizeof(char)));
   memset(cut_list, 0, new_cut->size * (max_shrink_cuts + 1));
   
   for (i = 1; i < vertnum; i++ ){
      if (verts[i].deleted) continue;/* for every node as a starting one */
      /*initialize the data structures */
      memset(in_set, 0, vertnum*sizeof(char));
      memset(cut_val, 0,vertnum* sizeof(double)); 
      in_set[i] = 1;
      set_size = 1 + verts[i].orig_node_list_size; 
      set_cut_val = 0;     
      for (e= verts[i].first; e; e = e-> next_edge){
	 weight = e->data->weight;
	 cut_val[e->other_end] = weight;
	 set_cut_val += weight;
      }
      set_demand = demand[i];  
      
      while(TRUE){ 
	 if (set_cut_val < 2*(ceil(set_demand/truck_cap)) - etol &&
	     set_size > 2){
	    memset(coef, 0, new_cut->size*sizeof(char));
	    /* printf("%d :", i); */
	    /*  printf("%d ", j); */
	    for (j = 1; j < vertnum; j++)
	       if (in_set[j]){
		  cur_nodept = verts + j;
		  if (cur_nodept->orig_node_list_size)
		     for (k = 0; k < cur_nodept->orig_node_list_size; k++)
			(coef[(cur_nodept->orig_node_list)[k] >>
			     DELETE_POWER]) |=
			   (1 << ((cur_nodept->orig_node_list)[k] &
				  DELETE_AND));
		  (coef[j>> DELETE_POWER]) |= (1 << ( j & DELETE_AND));
	       }
	    /*  printf("%f ", set_demand);
	    printf("%f \n",set_cut_val);*/ 
	    new_cut->type = (set_size < vertnum/2 ?
			     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	    new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
			     RHS((int)set_size,(int)set_demand,(int)truck_cap):
			     2*BINS((int)set_demand,(int)truck_cap));
	    for (k = 0, cutpt = cut_list; k < shrink_cuts; k++,
		    cutpt += new_cut->size)
		  if (!memcmp(coef, cutpt, new_cut->size*sizeof(char)))
		     break; /* same cuts */
	    if ( k >= shrink_cuts){
	       shrink_cuts +=
		  cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	       memcpy(cutpt, coef, new_cut->size);
	    }
	    
	    if ( shrink_cuts > max_shrink_cuts){
	       FREE(new_cut->coef);
	       return(shrink_cuts);
	    }
	 }
	 /* check the complement */
	  
	 complement_demand = total_demand - set_demand;
	 complement_cut_val =set_cut_val- 2*(*cut_val) + 2*num_routes; 
	 complement_size = vertnum - 1 - set_size;   
	 if (complement_cut_val< 2*(ceil(complement_demand/truck_cap))-etol &&
	     complement_size > 2){
	    memset(coef, 0, new_cut->size*sizeof(char));
	    for (j = 1; j < vertnum; j++)
	       if (!(in_set[j]) && !(verts[j].deleted)){ 
		  cur_nodept = verts + j;
		  if (cur_nodept->orig_node_list_size)
		     for (k = 0; k < cur_nodept->orig_node_list_size; k++)
			(coef[(cur_nodept->orig_node_list)[k] >>
			     DELETE_POWER]) |=
			   (1 << ((cur_nodept->orig_node_list)[k] &
				  DELETE_AND));
		  (coef[j>> DELETE_POWER]) |= (1 << ( j & DELETE_AND));
	       }
	    new_cut->type = (complement_size < vertnum/2 ?
			     SUBTOUR_ELIM_SIDE : SUBTOUR_ELIM_ACROSS);
	    new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
			     RHS((int)complement_size,(int)complement_demand,
				 (int)truck_cap):
			     2*BINS((int)complement_demand,(int)truck_cap));
	    for (k=0, cutpt = cut_list; k < shrink_cuts; k++,
		    cutpt += new_cut->size)
		  if (!memcmp(coef, cutpt, new_cut->size*sizeof(char))) break; 
	    if ( k >= shrink_cuts){
	       shrink_cuts +=
		  cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	       memcpy(cutpt, coef, new_cut->size);
	    }
	 
	    if (shrink_cuts > max_shrink_cuts){
	       FREE(new_cut->coef);
	       return(shrink_cuts);
	    }
	 }

	 for (maxval = -1, pt = in_set, dpt = cut_val,pt++, dpt++,
		 j = 1; j < vertnum; pt++, dpt++, j++){
	    if (!(*pt) && *dpt > maxval){
	       maxval = cut_val[j];
	       max_vert = j; 
	    }
	 }
	 if (maxval > 0){    /* add the vertex to the set */
	    in_set[max_vert] = 1;
	    set_size += 1 + verts[max_vert].orig_node_list_size ;
	    set_demand += demand[max_vert];
	    cut_val[max_vert] = 0;
	    for (e = verts[max_vert].first; e; e = e-> next_edge){
	       other_end = e->other_end;
	       weight = e->data->weight;
	       set_cut_val += (in_set[other_end]) ? (-weight): weight;
	       cut_val[other_end] += weight;
	       
	    }
	 }
	 else{ /* can't add anything to the set */
	    break;
	 }
      }   
   }
   FREE(new_cut->coef);
   return(shrink_cuts);
}

/*===========================================================================*/

int greedy_shrinking6_one(network *n, double truck_cap,
			  double etol, cut_data *new_cut,
			  char *in_set, double *cut_val, int num_routes,
			  char *cut_list, int max_shrink_cuts, int *demand,
			  int trial_num, double prob, cut_data ***cuts,
			  int *num_cuts, int *alloc_cuts)
{
  
   double set_cut_val, set_demand;
   vertex  *verts=n->verts;
   elist *e;
   int i, j, k, shrink_cuts = 0;
   char *pt, *cutpt;
   double  *dpt;
   int vertnum = n->vertnum;
   
   int max_vert = 0, set_size, begin = 1, end = 1, num_trials;
   char *coef;
   double maxval, r, q;
   double denominator = pow(2.0, 31.0) - 1.0;
   
   int other_end;
   double weight;

   double complement_demand, total_demand = verts[0].demand;
   double complement_cut_val; 
   int complement_size;
   vertex *cur_nodept; 
   /* int flag=0;*/
   
   new_cut->size = (vertnum >> DELETE_POWER) + 1;
   new_cut->coef = coef = (char *) (calloc(new_cut->size,sizeof(char)));
     memset(cut_list, 0, new_cut->size * (max_shrink_cuts +1));
  
   *in_set = 0;
 
   for (num_trials = 0; num_trials < trial_num*vertnum ; num_trials++){
      
      /*initialize the data structures */
      memset(in_set, 0, vertnum*sizeof(char));
      memset(cut_val, 0,vertnum* sizeof(double)); 
      
      set_cut_val = 0;
      set_size = 0;
      set_demand = 0;
      for (i = 1 ; i < vertnum; i++ ){
	 if (verts[i].deleted) continue;
	 r = (RANDOM()/denominator);
	 q = (prob/vertnum);
	 if (r < q){
	    in_set[i] = 1;
	    set_size += 1 + verts[i].orig_node_list_size;
	    set_demand += demand[i];
	    for (e = verts[i].first; e; e = e-> next_edge){
		other_end = e->other_end;
		weight  = e->data->weight;
		set_cut_val += (in_set[other_end]) ? (-weight) : weight;
		cut_val[other_end] += (in_set[other_end]) ? 0 : weight;
	    }
	 }
      }
      while(set_size){ 
	 if (set_cut_val < 2*(ceil(set_demand/truck_cap)) - etol &&
	     set_size > 2){
	    memset(coef, 0, new_cut->size*sizeof(char));
	    for (j = 1; j < vertnum; j++ )
	       if (in_set[j]){
		  cur_nodept = verts + j;
		  if (cur_nodept->orig_node_list_size)
		     for (k = 0; k < cur_nodept->orig_node_list_size; k++)
			(coef[(cur_nodept->orig_node_list)[k] >>
			     DELETE_POWER]) |=
			   (1 << ((cur_nodept->orig_node_list)[k] &
				  DELETE_AND));
		  (coef[j>> DELETE_POWER]) |= (1 << ( j & DELETE_AND));
	       }
	    new_cut->type = (set_size < vertnum/2 ?
			     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	    new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
			     RHS((int)set_size, (int)set_demand, (int)truck_cap):
			     2*BINS((int)set_demand, (int)truck_cap));
	    for (k = 0, cutpt = cut_list; k < shrink_cuts; k++,
		    cutpt += new_cut->size)
	       if (!memcmp(coef, cutpt, new_cut->size*sizeof(char))) break; 
	    if ( k >= shrink_cuts){
	       shrink_cuts +=
		  cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	       memcpy(cutpt, coef, new_cut->size);
	    }
	    if (shrink_cuts > max_shrink_cuts){
	       FREE(new_cut->coef);
	       return(shrink_cuts);
	    }
	 }
	 
	 /* check the complement */
	 
	 complement_demand = total_demand - set_demand;
	 complement_cut_val = set_cut_val - 2*(*cut_val) + 2*num_routes; 
	 complement_size = vertnum - 1 - set_size;   
	 if (complement_cut_val< 2*(ceil(complement_demand/truck_cap))-etol &&
	     complement_size > 2){
	    memset(coef, 0, new_cut->size*sizeof(char));
	    for (j = 1; j < vertnum; j++)
	       if (!(in_set[j])&& !(verts[j].deleted)){
		  cur_nodept = verts + j;
		  if (cur_nodept->orig_node_list_size)
		     for (k = 0; k < cur_nodept->orig_node_list_size; k++)
			(coef[(cur_nodept->orig_node_list)[k] >>
			     DELETE_POWER]) |=
			   (1 << ((cur_nodept->orig_node_list)[k] &
				  DELETE_AND));
		  (coef[j>> DELETE_POWER]) |= (1 << ( j & DELETE_AND));
	       }
	    new_cut->type = (complement_size  < vertnum/2 ?
			     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	    new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
			     RHS((int)complement_size,(int)complement_demand,
				 (int)truck_cap):
			     2*BINS((int)complement_demand,(int)truck_cap));
	    for (k = 0, cutpt = cut_list; k < shrink_cuts; k++,
		    cutpt += new_cut->size)
	       if (!memcmp(coef, cutpt, new_cut->size*sizeof(char))) break; 
	    if ( k >= shrink_cuts){
	       shrink_cuts +=
		  cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	       memcpy(cutpt, coef, new_cut->size);
	    }
	    
	    if (shrink_cuts > max_shrink_cuts){
	       FREE(new_cut->coef);
	       return(shrink_cuts);
	    }
	 }
	 
	 for (maxval = -1, pt = in_set + begin, dpt = cut_val + begin,
		 j = begin; j < end; pt++, dpt++, j++){
	    if (!(*pt) && *dpt > maxval){
	       maxval = cut_val[j];
		  max_vert = j; 
	    }
	 }
	 if (maxval > 0){    /* add the vertex to the set */
	    in_set[max_vert] = 1;
	    set_size += 1 + verts[max_vert].orig_node_list_size ;
	    set_demand += demand[max_vert];
	    cut_val[max_vert] = 0;
	    for (e = verts[max_vert].first; e; e = e-> next_edge){
	       other_end = e->other_end;
	       weight  = e->data->weight;
	       set_cut_val += (in_set[other_end]) ? (-weight) : weight;
	       cut_val[other_end] += weight;
	    }
	 }
	 else{ /* can't add anything to the set */
	    break;
	 }
      }   
   }

   FREE(new_cut->coef);
   return(shrink_cuts);
}

/*===========================================================================*/

int greedy_shrinking2_one(network *n, double truck_cap,
			  double etol, cut_data *new_cut,
			  char *in_set, double *cut_val, int num_routes,
			  int *demand, cut_data ***cuts, int *num_cuts,
			  int *alloc_cuts)
{
  
   double set_cut_val, set_demand;
   vertex *verts = n->verts;
   elist *e, *cur_edge1, *cur_edge2;
   int j, k, shrink_cuts = 0;
   char *pt;
   double  *dpt;
   int vertnum = n->vertnum;
   
   int max_vert = 0, set_size, begin = 1, end = 1;
   char *coef;
   double maxval;
   
   int other_end;
   double weight;

   double complement_demand, total_demand = verts[0].demand; 
   double complement_cut_val; 
   int complement_size;
   vertex *cur_nodept;
   
   new_cut->size = (vertnum >> DELETE_POWER) + 1;
   new_cut->coef =coef= (char *) (calloc(new_cut->size,sizeof(char)));
  
   *in_set=0;
   
   for (cur_edge1 = verts[0].first; cur_edge1;
	cur_edge1 = cur_edge1->next_edge){
      for (cur_edge2 = cur_edge1->next_edge; cur_edge2;
	   cur_edge2 = cur_edge2->next_edge){

	 /*initialize the data structures */
	 memset(in_set, 0, vertnum*sizeof(char));
	 memset(cut_val, 0,vertnum* sizeof(double)); 
	 
	 set_cut_val = 2;
	 set_size = 2 + cur_edge1->other->orig_node_list_size +
	    cur_edge2->other->orig_node_list_size;
	 set_demand = demand[cur_edge1->other_end] +
	    demand[cur_edge2->other_end];
	 in_set[cur_edge1->other_end] = 1;
	 
	 for (e = verts[cur_edge1->other_end].first; e; e = e-> next_edge){
	    cut_val[e->other_end] += e->data->weight;
	 }
	 
	 in_set[cur_edge2->other_end] = 1;
	 for (e = verts[cur_edge2->other_end].first; e; e = e-> next_edge){
	    other_end = e->other_end;
	    weight = e->data->weight;
	    set_cut_val += (in_set[other_end]) ? (-weight) : weight;
	    cut_val[other_end] += (in_set[other_end]) ? 0 : weight;
	 }
	 while(set_size){ 
	    if (set_cut_val < 2*(ceil(set_demand/truck_cap)) - etol &&
		set_size > 2){
	    memset(coef, 0, new_cut->size*sizeof(char));
	    for (j = 1; j < vertnum; j++ )
	       if (in_set[j]){
		  cur_nodept = verts + j;
		  if (cur_nodept->orig_node_list_size)
		     for (k = 0; k < cur_nodept->orig_node_list_size; k++)
			(coef[(cur_nodept->orig_node_list)[k] >>
			     DELETE_POWER]) |=
			   (1 << ((cur_nodept->orig_node_list)[k] &
				  DELETE_AND));
		  (coef[j >> DELETE_POWER]) |= (1 << (j & DELETE_AND));
	       }
	    new_cut->type = (set_size < vertnum/2 ?
			     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	    new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
			     RHS((int)set_size, (int)set_demand, (int)truck_cap):
			     2*BINS((int)set_demand, (int)truck_cap));
	    shrink_cuts +=
	       cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	 }

	 /* check the complement */
	 
	 complement_demand = total_demand - set_demand;
	 complement_cut_val = set_cut_val - 2*(*cut_val) + 2*num_routes; 
	 complement_size = vertnum - 1 - set_size;   
	 if (complement_cut_val< 2*(ceil(complement_demand/truck_cap))-etol &&
	     complement_size > 2){
	    memset(coef, 0, new_cut->size*sizeof(char));
	    for (j = 1; j < vertnum; j++)
	       if (!in_set[j]){
	       cur_nodept=verts + j;
		  if (cur_nodept->orig_node_list_size)
		     for (k = 0; k < cur_nodept->orig_node_list_size; k++)
			(coef[(cur_nodept->orig_node_list)[k] >>
			     DELETE_POWER]) |=
			   (1 << ((cur_nodept->orig_node_list)[k] &
				  DELETE_AND));
		  (coef[j>> DELETE_POWER]) |= (1 << ( j & DELETE_AND));
	       }
	    new_cut->type = (complement_size  < vertnum/2 ?
			     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	    new_cut->rhs =  (new_cut->type == SUBTOUR_ELIM_SIDE ?
			     RHS((int)complement_size,(int)complement_demand,
				 (int)truck_cap):
			     2*BINS((int)complement_demand,(int)truck_cap));
	    shrink_cuts +=
	       cg_send_cut(new_cut, num_cuts, alloc_cuts, cuts);
	 }
	 
	 for (maxval = -1, pt = in_set+begin, dpt = cut_val+begin,
		 j = begin; j < end; pt++, dpt++, j++){
	    if (!(*pt) && *dpt > maxval){
	       maxval = cut_val[j];
		  max_vert = j; 
	    }
	 }
	 if (maxval > 0){    /* add the vertex to the set */
	    in_set[max_vert] = 1;
	    set_size += 1 + verts[max_vert].orig_node_list_size ;
	    set_demand += demand[max_vert];
	    cut_val[max_vert] = 0;
	    for (e = verts[max_vert].first; e; e = e-> next_edge){
	       other_end = e->other_end;
	       weight  = e->data->weight;
	       set_cut_val += (in_set[other_end]) ? (-weight) : weight;
	       cut_val[other_end] += weight;
	    }
	 }
	 else{ /* can't add anything to the set */
	    break;
	 }
      }   
   }
   }
   FREE(new_cut->coef);
   return(shrink_cuts);
}

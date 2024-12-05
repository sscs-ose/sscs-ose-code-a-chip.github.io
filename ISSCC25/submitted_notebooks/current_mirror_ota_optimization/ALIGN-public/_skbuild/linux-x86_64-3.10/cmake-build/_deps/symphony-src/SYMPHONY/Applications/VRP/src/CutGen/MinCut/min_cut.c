#include <memory.h>
#include <stdlib.h>

#include "BB_constants.h"
#include "BB_macros.h"
#include "min_cut.h"
#include "vrp_macros.h"
#include "capforest.h"
#include "vrp_const.h"

/*---------------------------------------------------------------------------*\
| This routine finds small cuts in the network by applying the ideas of       |
| Nagamochi and Ibaraki                                                       |
\*---------------------------------------------------------------------------*/

int min_cut(cg_vrp_spec *vrp, network *n, double etol)
{
  cg_user_params *user_par = &vrp->par;
  float mincut = 2;
  register elist  *ne;
  register vertex *nv = NULL;
  register vertex *nu = NULL;
  register vertex *nw = NULL;
  int i, j;
  float contr_above = 2;
  float nodecut = 0;
  int vertnum = n->vertnum;
  int edgenum = n->edgenum;
  char scannedmark = 0;
  vertex **nen;
  int itnum =0;
  int cut_size = (vertnum >> DELETE_POWER) + 1;
  int total_demand = 0, capacity  = vrp->capacity, num_cuts = 0;
  cut_data *cut;
  char change_in_vertnum = TRUE, *coef;
  float max_q = 0;
  vertex *verts = n->verts;
  int v0, v1, cur_edge1_end;
  elist *cur_edge1, *cur_edge2, *cur_edge3, *prev_edge;
  
  /*allocate memory for existing nodes list and the binary tree used by
     capforest*/
  nen = n->enodes = (vertex **) calloc (n->vertnum, sizeof(vertex *));
  n->tnodes = (vertex **) calloc (n->vertnum, sizeof(vertex *));
   
  /*set up the data structure for the vertices*/
  for(i = 0, total_demand = 0; i < vertnum; i++){
    verts[i].scanned = 0;
    verts[i].orignodenum = i;
    verts[i].orig_node_list_size = 1;
    verts[i].orig_node_list = (char *) calloc (cut_size, sizeof(char));
    verts[i].orig_node_list[i >> DELETE_POWER] |= (1 << (i & DELETE_AND));
    total_demand += verts[i].demand;
  }
  
  /*shrink all the 1-edges in the current graph -- this operation preserves
    all small cuts in the graph and reduces the size of the problem*/
  num_cuts += shrink_one_edges(vrp, n, &vertnum, &edgenum, capacity, etol);

  cut = (cut_data *) calloc (1, sizeof(cut_data));
  cut->size = cut_size;
  coef = (char *) calloc (cut_size, sizeof(char));
  
  while (change_in_vertnum){/*if there hasn't been a change in the number of
			      vertices since the last iteration, then we are
			      done*/
    itnum++;
    change_in_vertnum = FALSE;
    
    scannedmark = 1-scannedmark;
    max_q = capforest(n, vertnum, scannedmark);/*construct the capacitated
						 forests
						 discussed by N-I*/
    contr_above = MIN(contr_above, max_q);/*reset the contraction limit*/
    
    /*--------------------------------------------------------------------*\
    | run through the list of "super nodes" and contract any edge whose    |
    | weight is above the limit "contr_above"                              |
    \*--------------------------------------------------------------------*/

    for( i=1; i<vertnum; i++){
      nv = nen[i];     /*get the next existing node*/
      ne = nv->first;  /*get the first edge in its adjacency list*/
      v0 = nv->orignodenum;   
      if (!v0) continue;  /*the depot should not be considered as part of any
			    cut*/

      /*-------------------------------------------------------------------*\
      | scan the adjacency list of this node and contract all eligible edges|
      | in its adjacency list                                               |
      \*-------------------------------------------------------------------*/

      while (ne != NULL){
	if ((ne->data->q >= contr_above - etol) && (ne->data->v0) &&
	    (ne->data->v1)){
	  v1 = OTHER_END(ne, v0);
	  nw = verts+v1; /*nw is a pointer to the other end vertex of the
			   current node*/

	  /*-----------------------------------------------------------------*\
	  | merge super node v0 with super node v1. "orig_node_list" is a bit |
	  | array containing the list of the original indices of nodes that   |
	  | have been contracted into this super node. the demand of the super|
	  | node is the sum of the demands of all the nodes that have been    |
	  | merged into it.                                                   |
	  \*-----------------------------------------------------------------*/
	  for (j = 0; j <cut_size; j++)
	    nv->orig_node_list[j] |= nw->orig_node_list[j];
	  nv->orig_node_list_size+=nw->orig_node_list_size;
	  nv->demand += nw->demand;
	  nw->scanned = TRUE;

	  /*-----------------------------------------------------------------*\
	  | Now update the adjacency lists to reflect the contraction of edge |
	  | (v0, v1) To do this, we scan through the adjacency list of node v1|
	  | For each of these edges, we look at the other end vertex of the   |
	  | edge Then there are two cases. if the other end vertex is not also|
	  | adjacent to vertex v0, then we simply change the edge data so that|
	  | it originates from v0 instead of v1. If on the other hand, the    |
	  | vertex in question is also adjacent to v0, then there already     |
	  | exists an edge from v0 to the vertex in question and in this case,|
	  | we have to sum the weights of the two edges that are now to       |
	  | originate from v0 and merge them into one edge.                   |
	  \*-----------------------------------------------------------------*/
	  for (cur_edge1 = nw->first; cur_edge1;
	       cur_edge1 = cur_edge1->next_edge){
	    cur_edge1_end = OTHER_END(cur_edge1, v1);/*get the other end of
						       the edge*/

	    for (cur_edge2 = nv->first, prev_edge = NULL; cur_edge2;
		 prev_edge = cur_edge2, cur_edge2 = cur_edge2->next_edge){
	      
	      /*---remove edge (v0, v1) from the adjacency list of v0--------*/
	      if ((OTHER_END(cur_edge2, v0)) == v1){
		cur_edge2->data->weight = 0;
		cur_edge2->data->deleted = TRUE;
		if (prev_edge)
		  prev_edge->next_edge = cur_edge2->next_edge;
		else
		  nv->first = cur_edge2->next_edge;
		if (!cur_edge2->next_edge) nv->last = prev_edge;
		nv->degree--;
		if (!nv->first) break;
	      }
	      
	      /*if cur_edge1_end is also adjacent to v0, then we must merge
		two edges*/
	      else if ((OTHER_END(cur_edge2, v0)) == cur_edge1_end){
		cur_edge2->data->weight += cur_edge1->data->weight;
		cur_edge1->data->deleted = TRUE;
		cur_edge1->data->weight = 0;
		nu = verts+cur_edge1_end;

	        /*check whether we have found a violated cut*/
		if ((user_par->do_extra_checking) && (cur_edge1_end) &&
		    (cur_edge2->data->weight > 2 -
		     BINS(nv->demand + nu->demand, capacity))){
		  cur_edge3 = nv->first;
		  nodecut = 0;
		  while (cur_edge3 != NULL){
		    if ((cur_edge3->data != cur_edge2->data) &&
			(cur_edge3->data != ne->data))
		      nodecut += cur_edge3->data->weight;
		    cur_edge3 = cur_edge3->next_edge;
		  }
		  cur_edge3 = nu->first;
		  while (cur_edge3 != NULL){
		    if ((cur_edge3->data != cur_edge2->data) &&
			(cur_edge3->data != cur_edge1->data))
		      nodecut += cur_edge3->data->weight;
		    cur_edge3 = cur_edge3->next_edge;
		  }
		  cur_edge3 = nw->first;
		  while (cur_edge3 != NULL){
		    if ((cur_edge3->data != cur_edge1->data) &&
			(cur_edge3->data != ne->data))
		      nodecut += cur_edge3->data->weight;
		    cur_edge3 = cur_edge3->next_edge;
		  }
		  /*if the cut is violated, then send it back to the LP*/
		  if (nodecut <
		      2*(BINS(nv->demand + nu->demand, capacity))- etol){
		    cut->type =
		      (nv->orig_node_list_size+nu->orig_node_list_size <
		       n->vertnum/2 ? SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
		    cut->rhs  =
		      (cut->type == SUBTOUR_ELIM_SIDE ?
		       RHS(nv->orig_node_list_size+nu->orig_node_list_size,
			   nv->demand+nu->demand, capacity):
		       2*(BINS(nv->demand + nu->demand, capacity)));
		    for (j = 0; j <cut_size; j++){
		      coef[j] = (nv->orig_node_list[j]|nu->orig_node_list[j]);
		    }
		    cut->coef = coef;
		    num_cuts += cg_send_cut(cut);
		  }
		} /*if ((cur_edge1_end) && (cur_edge2->data->weight > 2 - ...*/
		
	        nu->degree--;

		/*----update the adjacency list of cur_edge1_end------------*/
		for (prev_edge = NULL, cur_edge3 = nu->first;;
		     prev_edge = cur_edge3, cur_edge3 = cur_edge3->next_edge){
		  if ((OTHER_END(cur_edge3, cur_edge1_end)) == v1){
		    if (prev_edge){
		      prev_edge->next_edge = cur_edge3->next_edge;
		    }
		    else{
		      nu->first = cur_edge3->next_edge;
		    }
		    if (!cur_edge3->next_edge){
		      nu->last = prev_edge;
		    }
		    break;
		  }
		}
		cur_edge1->data->weight = 0;
	      } /*--else if ((OTHER_END(cur_edge2, v0)) == cur_edge1_end)*/
	    } /*--for (cur_edge2 = nv->first, prev_edge = NULL; cur_edge2;...*/
	    if (!nv->first) break;
	  } /*--for (cur_edge1 = nw->first; cur_edge1;...*/
	  
	  /*-----------------------------------------------------------------*\
	  | Now merge the remaining adjacency lists of v0 and v1              |
	  \*-----------------------------------------------------------------*/

	  for (cur_edge1 = nw->first; cur_edge1;
	       cur_edge1 = cur_edge1->next_edge){
	    if (cur_edge1){
	      if (cur_edge1->data->weight){
		if (nv->last){
		  nv->last->next_edge = cur_edge1;
		  nv->last = cur_edge1;
		  nv->degree++;
		  if (cur_edge1->data->v0 == v1)
		    cur_edge1->data->v0 = v0;
		  else
		    cur_edge1->data->v1 = v0;
		}
		else{
		  nv->first = nv->last = cur_edge1;
		  if (cur_edge1->data->v0 == v1)
		    cur_edge1->data->v0 = v0;
		  else
		    cur_edge1->data->v1 = v0;
		}
	      }
	    }
	  }
	  nv->last->next_edge = NULL;
	  nw->degree = 0;
	  nw->first = nw->last = NULL;

	  /*-----------------------------------------------------------------*\
	  | Now we update the existing node list. We want to delete v1 from   |
	  | the list but we have to be careful when we do this. We want to    |
	  | make sure that all the still existing nodes that have not been    |
	  | scanned yet in this iteration of the algorithm remain in a        |
	  | position in the array such that they will be scanned. In other    |
	  | words, in one of the positions with index >= i. There are several |
	  | cases that must be onsidered depending on where the node to be    |
	  | deleted is positioned in the existing nodes array                 |
	  \*-----------------------------------------------------------------*/
	  
	  if (nw->enodenum == i-1){
	    nen[nw->enodenum] = nen[--vertnum];
	    nen[vertnum]->enodenum = nw->enodenum;
	    i--;
	  }
	  else if (nw->enodenum < i-1){
	    nen[nw->enodenum] = nen[i-1];
	    nen[i-1]->enodenum = nw->enodenum;
	    nen[i-1] = nen[--vertnum];
	    nen[vertnum]->enodenum = i-1;
	    i--;
	  }
	  else{
	    nen[nw->enodenum] = nen[--vertnum];
	    nen[vertnum]->enodenum = nw->enodenum;
	  }
	  change_in_vertnum = TRUE;
	  edgenum--;

	  /*now check to see if the cut induced by super node v0 is violated*/
	  cur_edge1 = nv->first;
	  nodecut = 0;
	  while (cur_edge1 != NULL){
	    nodecut += cur_edge1->data->weight;
	    cur_edge1 = cur_edge1->next_edge;
	  }
	  if (nodecut < 2*(BINS(nv->demand, capacity)) - etol){
	    cut->type = (nv->orig_node_list_size < n->vertnum/2 ?
			 SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	    cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
			 RHS(nv->orig_node_list_size, nv->demand, capacity):
			 2*(BINS(nv->demand, capacity)));
	    cut->coef = nv->orig_node_list;
	    num_cuts += cg_send_cut(cut);
	  }
	  if (nodecut < mincut-etol){
	    mincut = nodecut;
	    if (user_par->update_contr_above)
	      contr_above = mincut;	      
	  }
	  ne = ne->next_edge;
	} /*---------if ((ne->data->q >= contr_above - etol) ...*/
	else{
	  ne = ne->next_edge;
	} /*---------if ((ne->data->q >= contr_above - etol) ...*/
      } /*-----------while (ne != NULL) */
    } /*-------------for( i=1; i<vertnum; i++)*/

    /*-----------------------------------------------------------------------*\
    | finally as an extra check, we can scan through all the nodes after each |
    | iteration is completely finished and see if the cuts induced by any of  |
    | these nodes are violated but this probably isn't necessary and may      |
    | result in the same cut being imposed several times                      |
    \*-----------------------------------------------------------------------*/
    
#if 0
    if ((vertnum > 1) && (user_par->do_extra_checking)){
      for ( i = 1; i<vertnum; i++ ){
	nodecut = 0;
	nv = nen[i];
	ne = nv->first;
	while (ne != NULL){
	  nodecut += ne->data->weight;
	  ne = ne->next_edge;
	}
	if (nodecut < 2*(BINS(nv->demand, capacity)) - etol){
	  cut->type = (nv->orig_node_list_size < n->vertnum/2 ?
		       SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	  cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
		       RHS(nv->orig_node_list_size, nv->demand, capacity):
		       2*(BINS(nv->demand, capacity)));
	  cut->coef = nv->orig_node_list;
	  num_cuts += cg_send_cut(cut);
	}
	if (nodecut < mincut-etol){
	  mincut = nodecut;
	  if (user_par->update_contr_above)
	    contr_above = mincut;	      
	}
      }
    }
    else
#endif
    contr_above = mincut;
  }

  FREE(coef);
  FREE(cut);
  
  n->mincut = mincut;

  for (i = 0; i < n->vertnum; i++)
    if (n->verts[i].orig_node_list)
      free((char *)n->verts[i].orig_node_list);
  free((char *)n->tnodes);
  free((char *)n->enodes);
  return(num_cuts);
}

/*===========================================================================*/

/*---------------------------------------------------------------------------*\
| This function shrinks 1-edges in the graph that are not adjacent to the     |
| depot                                                                       |
\*---------------------------------------------------------------------------*/

int shrink_one_edges(cg_vrp_spec *vrp, network *n, int *cur_verts,
		     int *cur_edges, int capacity, double etol)
{
  cg_user_params *user_par = &vrp->par;
  register vertex *nw;
  register vertex *nv = NULL;
  register vertex *nu;
  register elist *ne;
  register edge *dat = NULL;
  vertex **nen = n->enodes;
  int cut_size = (n->vertnum >> DELETE_POWER) + 1;
  vertex *verts = n->verts;
  int num_cuts = 0, itnum = 0;
  float nodecut;
  
  elist *new, *ne2, *nep, *prev;
  int vertnum = *cur_verts;
  int edgenum = 0;
  int i, j;
  cut_data *cut;
  char change_in_vertnum = TRUE, *coef;
  int v0, v1, cur_edge1_end;
  elist *cur_edge1, *cur_edge2, *cur_edge3, *np, *prev_edge;
  
  /*----------------------------------------------------------------------*\
  | First we contract all chains of 1-edges, called 1-paths. We simply look|
  | at all nodes of degree 2 and keep following the 1-path in each         |
  | direction from that node until we reach a node that is not of degree 2 |
  | Contracting chains is much easier to do than actually contracting all  |
  | the 1-edges and so we do it first                                      |
  \*----------------------------------------------------------------------*/

  cut = (cut_data *) calloc (1, sizeof(cut_data));
  cut->size = cut_size;
  coef = (char *) calloc (cut_size, sizeof(char));

  for (i = 1; i < vertnum - 1; i++){
    /*-----------check whether we have a degree 2 node-----------*/
    if ((verts[i].degree != 2) || (verts[i].scanned))
      continue;

    nv = verts+i;
    ne2 = (ne = nv->first)->next_edge;
    /*-----------------------------------------------------------------------*\
    | follow the 1-path from vertex i until we hit either the depot or a node |
    | that is not of degree 2                                                 |
    \*-----------------------------------------------------------------------*/
    for (nw = ne->other; nw->degree==2 && nw->orignodenum != 0; nw=ne->other){
      if (nw == nv){/*if we come back to the same node, that means we have a
		      subtour and we can simply impose the appropriate
		      constraint */
	cut->coef = nv->orig_node_list;
	cut->type = (nv->orig_node_list_size < n->vertnum/2 ?
		     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
		     RHS(nv->orig_node_list_size, nv->demand, capacity):
		     2*(BINS(nv->demand, capacity)));
	num_cuts += cg_send_cut(cut);
	nv->scanned = TRUE;
	nv->first = nv->last = NULL;
	break;
      }
      dat = ne->data;
      nep = ne;
      ne = nw->first;
      if (ne->data == dat)
	ne = ne->next_edge;
      if (!ne->other_end){
	ne = nep;
	break;
      }

      nw->scanned = TRUE;
      
      /*As we go along, we contract all the nodes on the 1-path into node i*/
      nv->demand += nw->demand;
      for (j = 0; j <cut_size; j++)
	nv->orig_node_list[j] |= nw->orig_node_list[j];
      nv->orig_node_list_size+=nw->orig_node_list_size;
      nw->first = nw->last = NULL;
      if (nv->demand > capacity){
	cut->coef = nv->orig_node_list;
	cut->type = (nv->orig_node_list_size < n->vertnum/2 ?
		     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
		     RHS(nv->orig_node_list_size, nv->demand, capacity):
		     2*(BINS(nv->demand, capacity)));
	num_cuts += cg_send_cut(cut);
      }
    } /*--for (nw = ne->other; nw->degree==2 && nw->orignodenum != 0;
	nw=ne->other)..*/

    if (nv->scanned) continue; /*in this case we had a subtour and so we don't
				 need to go on*/
    if (nw->orignodenum){ /*otherwise, nw is a pointer to one of the endpoints
			   of the 1-path. make new be the last edge on the
			   path that is adjacent to nw*/
      dat = ne->data;  
      for (ne=nw->first; ne->data != dat; ne=ne->next_edge);
      new = ne;
    }
    else{ /*this indicates that nw points to the depot which means that node i
	    is joined to the depot by a one edge. since we do not want to
	    contract one edges that are adjacent to the depot, we ignore this
	    edge and consider i to be the endpoint of the 1-path*/
      if (!((ne = nv->first)->other_end))
	ne=ne->next_edge;
      new = ne;
    }
    
    /*-----------------------------------------------------------------------*\
    | Now we find the other end point of the 1-path in a similar fashion      |
    \*-----------------------------------------------------------------------*/
    ne = ne2;
    for (nu = ne->other; nu->degree==2 && nu->orignodenum != 0;
	 nu = ne->other){
       dat = ne->data;
       nep = ne;
       ne = nu->first;
       if (ne->data == dat)
	  ne = ne->next_edge;
       if (!ne->other_end){
	  ne = nep;
	  break;
       }
       
       nu->scanned = TRUE;
       
       nv->demand += nu->demand;
       for (j = 0; j <cut_size; j++)
	  nv->orig_node_list[j] |= nu->orig_node_list[j];
       nv->orig_node_list_size+=nu->orig_node_list_size;
       nu->first = nu->last = NULL;
       if (nv->demand > capacity){
	  cut->coef = nv->orig_node_list;
	  cut->type = (nv->orig_node_list_size < n->vertnum/2 ?
		     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	  cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
		       RHS(nv->orig_node_list_size, nv->demand, capacity):
		       2*(BINS(nv->demand, capacity)));
	  num_cuts += cg_send_cut(cut);
       }
    }
    if(nu->orignodenum){
       dat = ne->data;
       for (ne=nu->first; ne->data != dat; ne=ne->next_edge);
    }
    else{
       if (!((ne = nv->first)->other_end))
	  ne = ne->next_edge;
    }
    
    /*-------------------------------------------------------------------*\
    | Now we update the adjacency lists appropriately. Remember that if   |
    | either nu or nw point to the depot, we must not consider these as   |
    | endpoints of the 1-path so we have several cases                    |
    \*-------------------------------------------------------------------*/

    if(nu->orignodenum && nw->orignodenum){
      dat = ne->data = new->data;
      ne->other = nw;
      new->other = nu;
      ne->data->v0 = nu->orignodenum;
      ne->data->v1 = nw->orignodenum;
      nv->scanned = TRUE;
      /*------------- contract nv into nu ----------------------------------*/
      nu->demand += nv->demand;
      for (j = 0; j <cut_size; j++)
	nu->orig_node_list[j] |= nv->orig_node_list[j];
      nu->orig_node_list_size+=nv->orig_node_list_size;
      nv->first = nv->last = NULL;
      /*-------- if nu induces a violated constraint, then impose it -------*/
      if (nu->demand > capacity){
	cut->coef = nu->orig_node_list;
	cut->type = (nu->orig_node_list_size < n->vertnum/2 ?
		     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
		     RHS(nu->orig_node_list_size, nu->demand, capacity):
		     2*(BINS(nu->demand, capacity)));
	num_cuts += cg_send_cut(cut);
      }
    }
    else if (!nu->orignodenum){/*in this case, nu points to the depot*/
      dat = ne->data = new->data;
      ne->other = nw;
      new->other = nv;
      ne->data->v0 = nw->orignodenum;
      ne->data->v1 = nv->orignodenum;
      nu = nv;
    }
    else if (!nw->orignodenum){/*in this case, nw points to the depot*/
      dat = ne->data = new->data;
      ne->other = nv;
      new->other = nu;
      ne->data->v0 = nu->orignodenum;
      ne->data->v1 = nv->orignodenum;
      nw = nv;
    }

    /*--------------------------------------------------------------------*\
    | finally we check to see if there is another edge connecting nu to nw.|
    | If so, then there must be a violated constraint since this implies a |
    | cut of less than two in the graph. Also, this requires a bit of care |
    | in updating the adjacency lists since then we will get a duplicate   |
    | edge between nu and nw                                               |
    \*--------------------------------------------------------------------*/
    
    for (prev = NULL, ne = nu->first; ne; prev = ne, ne = ne->next_edge){
      if ((ne->other == nw) && (ne->data != dat)){
	dat->weight += ne->data->weight;
	ne->data->weight = 0;
	ne->data->deleted = TRUE;
	if (prev)
	  prev->next_edge = ne->next_edge;
	else
	  nu->first = ne->next_edge;
	if (!ne->next_edge)
	  nu->last = prev;
	cut->type =
	  (nu->orig_node_list_size+nw->orig_node_list_size < n->vertnum/2 ?
	   SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
		     RHS(nu->orig_node_list_size+nw->orig_node_list_size,
			 nu->demand+nw->demand, capacity):
		     2*(BINS(nu->demand+nw->demand, capacity)));
	for (j = 0; j <cut_size; j++){
	  coef[j] = nu->orig_node_list[j] | nw->orig_node_list[j];
	}
	cut->coef = coef;
	num_cuts += cg_send_cut(cut);
	for (prev = NULL, ne = nw->first; ne; prev = ne, ne = ne->next_edge){
	  if (ne->data->deleted){
	    if (prev)
	      prev->next_edge = ne->next_edge;
	    else
	      nw->first = ne->next_edge;
	    if(!ne->next_edge)
	      nw->last = prev;
	    break;
	  }
	}
	break;
      }
    }
  }

  /*----- here we construct the list of existing nodes ----------------*/
  for (i=0, j = 0; i<vertnum; j++){
    if (!verts[j].scanned){
      nen[i] = verts+j;
      verts[j].enodenum = i;
      i++;
      edgenum += verts[j].degree;
    }else{
      vertnum--;
    }
  }
  edgenum /= 2;

  if (!user_par->shrink_one_edges){
    *cur_verts = vertnum;
    *cur_edges = edgenum;
    return(num_cuts);
  }

  /*-----------------------------------------------------------------------*\
  | Here we can optionally shrink all the 1-edges in the graph. I am not    |
  | sure whether this is advantageous or not but it makes it easier to spot |
  | violated cuts. These edges would get contracted anyway in the next phase|
  | of this algorithm but it might make sense to contract them beforehand.  |
  | The rest of this function is uncommented because it is exactly the same |
  | as the main loop in the min_cut routine except that we only consider    |
  | 1-edges for contraction instead of any edge above the threshold         |
  \*-----------------------------------------------------------------------*/
  
  while (change_in_vertnum){
    itnum++;
    change_in_vertnum = FALSE;
    for( i=1; i<vertnum; i++){
      nv = nen[i];
      ne = nv->first;
      v0 = nv->orignodenum;
      while (ne != NULL){
	if ((ne->data->weight >= 1 - etol) && (ne->data->v0) &&
	    (ne->data->v1)){
	  v1 = OTHER_END(ne, v0);
	  nw = verts+v1;
	  for (j = 0; j <cut_size; j++)
	    nv->orig_node_list[j] |= nw->orig_node_list[j];
	  nv->orig_node_list_size+=nw->orig_node_list_size;
	  nv->demand += nw->demand;
	  nw->scanned = TRUE;
	  if (nv->demand > capacity){
	    cut->coef = nv->orig_node_list;
	    cut->type = (nv->orig_node_list_size < n->vertnum/2 ?
			 SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	    cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
			 RHS(nv->orig_node_list_size, nv->demand, capacity):
			 2*(BINS(nv->demand, capacity)));
	    num_cuts += cg_send_cut(cut);
	  }

	  for (cur_edge1 = nw->first; cur_edge1;
	       cur_edge1 = cur_edge1->next_edge){
	    if ((cur_edge1_end = OTHER_END(cur_edge1, v1)) == v0){
	      cur_edge1->data->weight = 0;
	      cur_edge1->data->deleted = TRUE;
	    }

	    for (cur_edge2 = nv->first, prev_edge = NULL; cur_edge2;
		 prev_edge = cur_edge2, cur_edge2 = cur_edge2->next_edge){
	      if ((OTHER_END(cur_edge2, v0)) == v1){
		cur_edge2->data->weight = 0;
		cur_edge2->data->deleted = TRUE;
		if (prev_edge)
		  prev_edge->next_edge = cur_edge2->next_edge;
		else
		  nv->first = cur_edge2->next_edge;
		if (!cur_edge2->next_edge) verts[v0].last = prev_edge;
		nv->degree--;
		if (!nv->first) break;
	      }
	      else if ((OTHER_END(cur_edge2, v0)) == cur_edge1_end){
		cur_edge2->data->weight += cur_edge1->data->weight;
		cur_edge1->data->deleted = TRUE;
		cur_edge1->data->weight = 0;
		nu = verts + cur_edge1_end;
		if ((cur_edge1_end) && (cur_edge2->data->weight > 2 - 
		    BINS(nv->demand + nu->demand, capacity) + etol)){
		  cut->type =
		    (nv->orig_node_list_size+nu->orig_node_list_size <
		     n->vertnum/2 ? SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
		  cut->rhs  =
		    (cut->type == SUBTOUR_ELIM_SIDE ?
		     RHS(nv->orig_node_list_size+nu->orig_node_list_size,
			 nv->demand+nu->demand, capacity):
		     2*(BINS(nv->demand+nu->demand, capacity)));
		  for (j = 0; j <cut_size; j++){
		    coef[j] = nv->orig_node_list[j] | nu->orig_node_list[j];
		  }
		  cut->coef = coef;
		  num_cuts += cg_send_cut(cut);
		}
		nu->degree--;
		for (prev_edge = NULL, cur_edge3 = nu->first;;
		     prev_edge = cur_edge3, cur_edge3 = cur_edge3->next_edge){
		  if ((OTHER_END(cur_edge3, cur_edge1_end)) == v1){
		    if (prev_edge){
		      prev_edge->next_edge = cur_edge3->next_edge;
		    }
		    else{
		      nu->first = cur_edge3->next_edge;
		    }
		    if (!cur_edge3->next_edge){
		      nu->last = prev_edge;
		    }
		    break;
		  }
		}
		cur_edge1->data->weight = 0;
	      }
	    }
	    if (!nv->first) break;
	  }
	  
	  for (cur_edge1 = nw->first; cur_edge1;
	       cur_edge1 = cur_edge1->next_edge){
	    if (cur_edge1){
	      if (cur_edge1->data->weight){
		if (nv->last){
		  nv->last->next_edge = cur_edge1;
		  nv->last = cur_edge1;
		  nv->degree++;
		  if (cur_edge1->data->v0 == v1)
		    cur_edge1->data->v0 = v0;
		  else
		    cur_edge1->data->v1 = v0;
		}
		else{
		  nv->first = nv->last = cur_edge1;
		  if (cur_edge1->data->v0 == v1)
		    cur_edge1->data->v0 = v0;
		  else
		    cur_edge1->data->v1 = v0;
		}
	      }
	    }
	  }
	  nv->last->next_edge = NULL;
	  nw->degree = 0;
	  nw->first = nw->last = NULL;
	  if (nw->enodenum == i-1){
	    nen[nw->enodenum] = nen[--vertnum];
	    nen[vertnum]->enodenum = nw->enodenum;
	    i--;
	  }
	  else if (nw->enodenum < i-1){
	    nen[nw->enodenum] = nen[i-1];
	    nen[i-1]->enodenum = nw->enodenum;
	    nen[i-1] = nen[--vertnum];
	    nen[vertnum]->enodenum = i-1;
	    i--;
	  }
	  else{
	    nen[nw->enodenum] = nen[--vertnum];
	    nen[vertnum]->enodenum = nw->enodenum;
	  }
	  change_in_vertnum = TRUE;
	  edgenum--;
	  np = ne;
	  ne = ne->next_edge;
	}
	else{
	  np = ne;
	  ne = ne->next_edge;
	}
      }
    }
  }

  if ((vertnum > 1) && (user_par->do_extra_checking)){
    for ( i = 1; i<vertnum; i++ ){
      nodecut = 0;
      nv = nen[i];
      ne = nv->first;
      while (ne != NULL){
	nodecut += ne->data->weight;
	ne = ne->next_edge;
      }
      if (nodecut < 2*(BINS(nv->demand, capacity)) - etol){
	cut->type = (nv->orig_node_list_size < n->vertnum/2 ?
		     SUBTOUR_ELIM_SIDE:SUBTOUR_ELIM_ACROSS);
	cut->rhs  = (cut->type == SUBTOUR_ELIM_SIDE ?
		     RHS(nv->orig_node_list_size, nv->demand, capacity):
		     2*(BINS(nv->demand, capacity)));
	cut->coef = nv->orig_node_list;
	num_cuts += cg_send_cut(cut);
      }
    }
  }
  
  *cur_verts = vertnum;
  *cur_edges = edgenum;

  FREE(coef);
  FREE(cut);

  return(num_cuts);  
}

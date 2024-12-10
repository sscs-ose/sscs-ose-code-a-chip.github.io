#include <stdio.h>

#include "capforest.h"

#define tnodenum degree

/*=======================================================================*/

/* This routine builds up the "capacitated forests" as it is 
   in the Nagamochi - Ibaraki paper */

float capforest(network *n, int Vertnum, char scannedmark)
{
  int i;
  int last_tnode;
  register vertex *nv = NULL;
  register elist *ne;
  register edge *ned;
  vertex **tnodes = n->tnodes;
  vertex **nen = n->enodes;
  int nomark = 1-scannedmark;
  float max_q = 0;

  /*------------------- Initialization -------------*/
  
  for (i=0; i<Vertnum; i++){
    nv = nen[i];
    nv->r = 0;
    ne=nv->first;
    do{
      ne->data->q = 0;
      ne->data->scanned = nomark;  /*this is unnecessary*/
    }while ((ne=ne->next_edge) != NULL);
  }
  
  last_tnode = 0;
  
  /*------------------- The big while loop ---------*/
  
  do{
    ne=nv->first;
    do{
      if ((ned=ne->data)->scanned != scannedmark){
	ned->scanned = scannedmark;
	ned->q = increment((n->verts)+(OTHER_END(ne, nv->orignodenum)),
			   ned->weight, tnodes, &last_tnode);
	if (ned->q > max_q) max_q = ned->q;
      }
    }while ((ne=ne->next_edge) != NULL);
    nv = delmax(tnodes, &last_tnode);
  }while (last_tnode != 0);
  return(max_q);
}

/*=======================================================================*/

vertex *delmax(tnodes, ltn)
  vertex **tnodes;
  int *ltn;
{
  vertex *temp, *retnode;
  int last = *ltn;
  int pos, ch;
  float actual;
  
  retnode = tnodes[1];
  temp = tnodes[1] = tnodes[last];
  actual = temp->r;
  *ltn = --last;
  pos = 1;
  while ((ch=2*pos) < last){
    if (tnodes[ch]->r < tnodes[ch+1]->r)
      ch++;
    if (actual >= tnodes[ch]->r){
      tnodes[pos] = temp;
      temp->tnodenum = pos;
      return(retnode);
    }
    tnodes[pos] = tnodes[ch];
    tnodes[ch]->tnodenum = pos;
    pos = ch;
  }
  if (ch == last){
    if (actual < tnodes[ch]->r){
      tnodes[pos] = tnodes[ch];
      tnodes[ch]->tnodenum = pos;
      pos=ch;
    }
  }
  tnodes[pos] = temp;
  temp->tnodenum = pos;
  return(retnode);
}

/*=======================================================================*/

float increment(vertex *v, float inc, vertex **tnodes, int *ltn)
{
  float actval;
  int pos, ch;
  int last = *ltn;
  
  if (v->r == 0){   /* We have to insert it into the tree */
    *ltn = ++last;
    pos = last;
  }else{
    pos = v->tnodenum;
  }
  
  /*************
    pos = (v->r == 0) ? (*ltn = ++last) : v->tnodenum;
    *************/
  actval = (v->r += inc);
  
  while ((ch=pos/2) != 0){
    if (tnodes[ch]->r < actval){
      tnodes[pos] = tnodes[ch];
      tnodes[ch]->tnodenum = pos;
      pos = ch;
    }else{
      tnodes[pos] = v;
      v->tnodenum = pos;
      return(actval);
    }
  }
  tnodes[pos] = v;
  v->tnodenum = pos;
  return(actval);
}

/*=======================================================================*/

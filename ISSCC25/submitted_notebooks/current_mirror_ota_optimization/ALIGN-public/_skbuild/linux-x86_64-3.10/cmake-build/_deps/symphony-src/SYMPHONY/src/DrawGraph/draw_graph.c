/*===========================================================================*/
/*                                                                           */
/* This file is part of the SYMPHONY MILP Solver Framework.                  */
/*                                                                           */
/* SYMPHONY was jointly developed by Ted Ralphs (ted@lehigh.edu) and         */
/* Laci Ladanyi (ladanyi@us.ibm.com).                                        */
/*                                                                           */
/* The Interactive Graph Drawing application was developed by Marta Eso.     */
/*                                                                           */
/* (c) Copyright 2000-2019 Ted Ralphs. All Rights Reserved.                  */
/*                                                                           */
/* This software is licensed under the Eclipse Public License. Please see    */
/* accompanying file for terms.                                              */
/*                                                                           */
/*===========================================================================*/

#if defined(_MSC_VER) || defined (__MNO_CYGWIN)
#include <io.h>
#define execlp _execlp
#include <process.h>
#else
#include <unistd.h>
#endif
#include <memory.h>
#include <fcntl.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdarg.h>

#include "sym_constants.h"
#include "sym_macros.h"
#include "sym_proccomm.h"
#include "sym_messages.h"
#include "sym_dg.h"
#include "sym_dg_params.h"

/*===========================================================================*/

void INTERMED_ERROR(char *window_name, int old_msgtag,
		    int receiver, int msgtag)
{
   int s_bufid;
   s_bufid = init_send(DataInPlace);
   send_char_array(window_name, MAX_NAME_LENGTH);
   send_int_array(&old_msgtag, 1);
   send_msg(receiver, msgtag);
   freebuf(s_bufid);
}

/*===========================================================================*/

static int echo_commands;
int spprint(FILE *write_to, const char *format, ...)
{
   int i;
   va_list ap;

   va_start(ap, format);
   if (echo_commands) vprintf(format, ap);
   va_end(ap);
   va_start(ap, format);
   i = vfprintf(write_to, format, ap);
   va_end(ap);
   return(i);
}

/*===========================================================================*/

/*===========================================================================*\
 * Exec the named cmd as a child process, returning two pipes to
 * communicate with the process, and the child's process ID.
\*===========================================================================*/

int start_child(char *cmd, FILE **readpipe, FILE **writepipe)
{

   /* FIXME: Doesn't seem to work for Windows */
   
#if !defined(_MSC_VER) && !defined (__MNO_CYGWIN)

   int childpid, pipe1[2], pipe2[2];

#if !defined(_MSC_VER) && !defined (__MNO_CYGWIN)
   if ((pipe(pipe1) < 0) || (pipe(pipe2) < 0)){
      perror("pipe");
      exit(-1);
   }
#else
   if ((_pipe(pipe1,256,O_BINARY) < 0) || (_pipe(pipe2,256,O_BINARY) < 0)){
      perror("pipe");
      exit(-1);
   }
#endif

   if ((childpid = vfork()) < 0){
      perror("fork");
      exit(-1);
   }else if (childpid > 0){    /* parent */
      close(pipe1[0]);
      close(pipe2[1]);
      /* write to child is pipe1[1], read from child is pipe2[0] */
      *readpipe = fdopen(pipe2[0], "r");
      /* this sets the pipe to be a Non-Blocking IO one, so fgets won't wait
       * until it receives a line. */
      fcntl(pipe2[0], F_SETFL, O_NONBLOCK);
      *writepipe = fdopen(pipe1[1], "w");
      setlinebuf(*writepipe);
      return(childpid);
   }else{      /* child */
      close(pipe1[1]);
      close(pipe2[0]);
      /* read from parent is pipe1[0], write to parent is pipe2[1] */
      dup2(pipe1[0], 0);
      dup2(pipe2[1], 1);
      close(pipe1[0]);
      close(pipe2[1]);
      if (execlp(cmd, cmd, NULL) < 0)
	 perror("execlp");

      /* never returns */
   }

#endif

   return(0);
}

/*===========================================================================*/

int main(void)
{
   dg_prob *dgp;
   dg_params *par;
   FILE *read_from, *write_to;
   int childpid, sender;

   char tcl_msg[MAX_LINE_LENGTH +1];
   char name[MAX_NAME_LENGTH +1], name2[MAX_NAME_LENGTH +1];
   char source[MAX_NAME_LENGTH +1], target[MAX_NAME_LENGTH +1];
   char title[MAX_TITLE_LENGTH +1], title2[MAX_TITLE_LENGTH +1];
   char fname[MAX_FILE_NAME_LENGTH +1];
   char old_weight[MAX_WEIGHT_LENGTH +1], new_weight[MAX_WEIGHT_LENGTH +1];
   char new_label[MAX_LABEL_LENGTH +1];
   char new_dash[MAX_DASH_PATTERN_LENGTH +1];
   char *str;
   int msgtag, keyword, key, r_bufid, s_bufid, bufid, bytes, len;

   int i, j, k, number, add_nodenum, change_nodenum, delete_nodenum;
   int add_edgenum, change_edgenum, delete_edgenum;
   int nodenum, new_nodenum, edgenum, new_edgenum, node_id, edge_id;
   int new_radius, old_deleted_nodenum;
   unsigned int id;
   win_desc *desc;
   dg_graph *g;
   dg_node *nodes, *nod;
   dg_edge *edges, *edg;
   window *win, *new_win, *source_win, *target_win;

   register_process();
   dgp = (dg_prob *) calloc(1, sizeof(dg_prob));

   /* receive parameters from the master */
   r_bufid = receive_msg(ANYONE, DG_DATA);
   bufinfo(r_bufid, &bytes, &msgtag, &dgp->master);
   receive_char_array((char *)&dgp->par, sizeof(dg_params));
   freebuf(r_bufid);
   par = &(dgp->par);
   echo_commands = par->echo_commands;

   /* fork the wish shell */
   childpid = start_child((char *)"wish", &read_from, &write_to);

   /* Source the tcl scripts into wish and invoke startUp*/
   spprint(write_to, "source %s/Init.tcl\n", par->source_path);
   spprint(write_to, "source %s/Tools.tcl\n", par->source_path);
   spprint(write_to, "source %s/NodeEdgeBasics.tcl\n", par->source_path);
   spprint(write_to, "source %s/FileMenu.tcl\n", par->source_path);
   spprint(write_to, "source %s/WindowMenu.tcl\n", par->source_path);
   spprint(write_to, "source %s/NodeMenu.tcl\n", par->source_path);
   spprint(write_to, "source %s/EdgeMenu.tcl\n", par->source_path);
   spprint(write_to, "source %s/CAppl.tcl\n", par->source_path);

   spprint(write_to, "Igd_StartUp\n");

   /* set application defaults to those stored in par */
   spprint(write_to,
	   "Igd_SetApplDefaults %i %i %i %i %i %i %i {%s} {%s} %i %i %i %f {%s} {%s} {%s}\n",
	   par->canvas_width, par->canvas_height, par->viewable_width,
	   par->viewable_height, par->disp_nodelabels,
	   par->disp_nodeweights, par->disp_edgeweights, par->node_dash,
	   par->edge_dash, par->node_radius, par->interactive_mode,
	   par->mouse_tracking, par->scale_factor, par->nodelabel_font,
	   par->nodeweight_font, par->edgeweight_font);

   /* invoke user initialization */
#ifdef USE_SYM_APPLICATION
   CALL_USER_FUNCTION( user_initialize_dg(&dgp->user) );
#endif

   while(TRUE){

      msgtag = 0;

      if (dgp->waiting_to_die){
	 for ( i = 0; i < dgp->window_num; ){
	    if ( ! dgp->windows[i]->wait_for_click ){
	       spprint(write_to, "Igd_QuitWindow %u\n",dgp->windows[i]->id);
	       free_window(&dgp->window_num, dgp->windows, i);
	    }else{
	       i++;
	    }
	 }
	 if ( ! dgp->window_num )
	    wait_for_you_can_die(dgp, write_to);
      }

      /* Interpret message coming from the tcl application. */
      if (fgets(tcl_msg, 80, read_from) != NULL) {
	 sscanf(tcl_msg, "%i", &msgtag);

	 switch(msgtag){

	  case IGDTOI_CLICK_HAPPENED:
	    /* if wait_for_click is 2, send a message to the owner */
	    fgets(name2, MAX_NAME_LENGTH +1, read_from);
	    sscanf(name2, "%u", &id);
	    for (i = dgp->window_num - 1; i >= 0; i-- )
	       if ( dgp->windows[i]->id == id )
		  break;
	    if ( i < 0 ) {
	       /* this should never happen */
	       printf("Window of id %u is not found\n", id);
	       break;
	    }
	    if ( dgp->windows[i]->wait_for_click == 2 ) {
	       s_bufid = init_send(DataInPlace);
	       send_str(name);
	       send_msg(dgp->windows[i]->owner_tid, ITOC_CLICK_HAPPENED); 
	       freebuf(s_bufid); 
	    }
	    dgp->windows[i]->wait_for_click = 0;
	    break;

	  case IGDTOI_QUIT_WINDOW:
	    /* delete data structure corresponding to this window */
	    fgets(name2, MAX_NAME_LENGTH +1, read_from);
	    sscanf(name2, "%u", &id);
	    for (i = dgp->window_num - 1; i >= 0; i-- )
	       if ( dgp->windows[i]->id == id )
		  break;
	    if ( i < 0 ) {
	       /* this should never happen */
	       printf("Window of id %u is not found\n", id);
	       break;
	    }
	    spprint(write_to, "Igd_QuitWindow %u\n", id);
	    free_window(&dgp->window_num, dgp->windows, i);
	    break;

	  case IGDTOI_QUIT_APPLICATION:
	    /* delete all windows */
	    for ( i = 0; i < dgp->window_num; ){
	       if ( ! dgp->windows[i]->wait_for_click ){
		  spprint(write_to, "Igd_QuitWindow %u\n",dgp->windows[i]->id);
		  free_window(&dgp->window_num, dgp->windows, i);
	       }else{
		  i++;
	       }
	    }
	    dgp->waiting_to_die = TRUE;
	    break;

	  case IGDTOI_TEXT_ENTERED:
	    fgets(name2, MAX_NAME_LENGTH +1, read_from);
	    sscanf(name2, "%u", &id);
	    for (i = dgp->window_num - 1; i >= 0; i-- )
	       if ( dgp->windows[i]->id == id )
		  break;
	    win = dgp->windows[i];
	    if ( i < 0 ) {
	       /* this should never happen */
	       printf("Window of id %u is not found\n", id);
	       break;
	    }
	    fgets(tcl_msg, MAX_LINE_LENGTH +1, read_from);
	    sscanf(tcl_msg, "%i", &win->text_length);
	    win->text = (char *) malloc( (win->text_length + 1) * CSIZE);
	    fread(win->text, CSIZE, win->text_length, read_from);
	    win->text[win->text_length] = 0;

	    /* invoke function that interprets the message */
#ifdef USE_SYM_APPLICATION
	    CALL_USER_FUNCTION( user_interpret_text(dgp->user,
						    win->text_length,
						    win->text,
						    win->owner_tid) );
#endif
	    break;

	  case IGDTOI_REQUEST_GRAPH:
	    fgets(name2, MAX_NAME_LENGTH +1, read_from);
	    sscanf(name2, "%u", &id);
	    for (i = dgp->window_num - 1; i >= 0; i-- )
	       if ( dgp->windows[i]->id == id )
		  break;
	    if ( i < 0 ) {
	       /* this should never happen */
	       printf("Window of id %u is not found\n", id);
	       break;
	    }
	    display_graph_on_canvas(dgp->windows[i], write_to);
	    break;

	  default:
	    printf("Unknown message type from IGD to I (%i)\n", msgtag);
	    break;
	 
	 } /* end switch */
      } /* end if */

      if (dgp->waiting_to_die)
	 continue;


      /* Interpret the message coming from the C application.

	 All the messages except INITIALIZE_WINDOW and COPY_GRAPH
	 and QUIT will be put on the pipe corresponding to the appropriate
	 window (messages are processed in FIFO order

	 In case of INITIALIZE_WINDOW the data structure associated
	 with a winow is created (including the pipes.

	 In case of COPY_GRAPH a message must be placed on both the
	 source and the target window's pipe.

	 In case of QUIT all data structures are disassembled and then
	 the tcl application is killed.                                   */

      r_bufid = nreceive_msg(ANYONE, ANYTHING);
      if (r_bufid > 0){
	 bufinfo(r_bufid, &bytes, &msgtag, &sender);
	 switch (msgtag){

	  case CTOI_INITIALIZE_WINDOW:

	    /* get the name of the new window */
	    receive_str(name);
	    receive_str(title);

	    /* if a window with this name already exists: error */
	    i = find_window(dgp->window_num, dgp->windows, name);
	    if ( i >= 0 ) {
	       INTERMED_ERROR(name, msgtag, sender,ITOC_WINDOW_ALREADY_EXISTS);
	       freebuf(r_bufid);
	       break;
	    }
	    /* allocate space for the new window */
	    win = init_dgwin(dgp, sender, name, title);

	    /* set up the window description */
	    receive_int_array(&number, 1);
	    copy_win_desc_from_par(win, &dgp->par);
	    for ( ; number > 0; number-- ) {
	       /* read out the key - value pairs */
	       receive_int_array(&key, 1);
	       set_window_desc_pvm(key, win);
	    }

	    freebuf(r_bufid);
	    break;


	  case CTOI_COPY_GRAPH:
	    /* Copy source's graph into target's window.
	       Here a message is placed onto both target's and source's
	       pipe so that they can wait for each other before the
	       actual copying happens (shake hands) */
	    
	    receive_str(target);
	    receive_str(source);

	    i = find_window(dgp->window_num, dgp->windows, target);
	    if (i < 0) { /* target doesn't exist, send error message */
	       INTERMED_ERROR(target, msgtag, sender,ITOC_WINDOW_DOESNT_EXIST);
	       freebuf(r_bufid);
	       break;
	    }
	    j = find_window(dgp->window_num, dgp->windows, source);
	    if (j < 0) { /* source doesn't exist, send error message */
	       INTERMED_ERROR(source, msgtag, sender,ITOC_WINDOW_DOESNT_EXIST);
	       freebuf(r_bufid);
	       break;
	    }
	    bufid = init_send(DataInPlace);
	    msgtag = WAITING_TO_GET_A_COPY;
	    send_int_array(&msgtag, 1);
	    send_str(source);
	    add_msg(dgp->windows[i], bufid);
	    setsbuf(0);

	    bufid = init_send(DataInPlace);
	    msgtag = WAITING_TO_BE_COPIED;
	    send_int_array(&msgtag, 1);
	    send_str(target);
	    add_msg(dgp->windows[j], bufid);
	    setsbuf(0);

	    freebuf(r_bufid);
	    break;


	  case CTOI_QUIT:
	    /* quit from all windows, disassemble data structures.
	     * (actually, this will happen on the top of the while loop...) */
	    if (! dgp->waiting_to_die)
	       dgp->waiting_to_die = TRUE;
	    freebuf(r_bufid);
	    break;

	  case CTOI_YOU_CAN_DIE:
	    /* quit from all windows, disassemble data structures.
	     * (actually, this will happen on the top of the while loop...)
	     * and die */
	    dgp->waiting_to_die = 2 * TRUE;
	    freebuf(r_bufid);
	    break;


	  default:
	    /* Check if window with name exists. If not, send back error
	       message. If yes, copy the message over to window's pipe. */
	    receive_str(name);
	    len = strlen(name);
	    i = find_window(dgp->window_num, dgp->windows, name);
	    if (i < 0){
	       /* there is no window of that name: send error message */
	       INTERMED_ERROR(name, msgtag, sender,ITOC_WINDOW_DOESNT_EXIST);
	       freebuf(r_bufid);
	       break;
	    }

	    add_msg(dgp->windows[i], r_bufid);
	    setrbuf(0);
	    break;
	 } /* end switch */
      } /* endif r_bufid > 0 */


      if (dgp->waiting_to_die)
	 continue;

      /* Process one message from each window's pipe. */

      for ( i = 0; i < dgp->window_num; i++ ) {

	 win = dgp->windows[i];

	 /* if wait_for_click is set, skip */
	 if ( win->wait_for_click )
	    continue;

	 /* if window is waiting to be copied or waiting to get a copy, skip */
	 if ( win->copy_status )
	    continue;

	 /* if no message in the pipe, skip */
	 if (win->buf.bufread == -1)
	    continue;

	 /* else: process the message .... */
	 msgtag = 0;
	 r_bufid = get_next_msg(win);
	 setrbuf(r_bufid);
	 bufinfo(r_bufid, &bytes, &msgtag, &sender);

	 if (msgtag == 0){
	    /* This means that the message was locally 'hand-packed' */
	    receive_int_array(&msgtag, 1);
	 }

	 switch ( msgtag ) {

	  case CTOI_USER_MESSAGE:
#ifdef USE_SYM_APPLICATION
	    user_dg_process_message(win->user, win, write_to);
#endif
	    break;

	  case CTOI_QUIT_WINDOW:
	    /* delete this window */
	    spprint(write_to, "Igd_QuitWindow %u\n", win->id);
	    free_window(&dgp->window_num, dgp->windows, i);
	    i--;
	    break;


	  case CTOI_CHANGE_WINDOW_DESC:
	    /* change window descriptions */
	    receive_int_array(&number, 1);
	    for ( ; number > 0; number-- ) {
	       /* read out the key - value pairs */
	       receive_int_array(&key, 1);
	       set_window_desc_pvm(key, win);
	    }
	    desc = &(win->desc);
	    if ( win->window_displayed ) {
	       spprint(write_to, "Igd_SetAndExecuteWindowDesc %u %i %i %i %i %i %i %i {%s} {%s} %i %i %i %f {%s} {%s} {%s}\n",
		       win->id, desc->canvas_width, desc->canvas_height,
		       desc->viewable_width, desc->viewable_height,
		       desc->disp_nodelabels, desc->disp_nodeweights,
		       desc->disp_edgeweights, desc->node_dash,
		       desc->edge_dash, desc->node_radius,
		       desc->interactive_mode, desc->mouse_tracking,
		       desc->scale_factor, desc->nodelabel_font,
		       desc->nodeweight_font, desc->edgeweight_font);
	    }
	    break;


	  case CTOI_SET_GRAPH:
	  case CTOI_SET_AND_DRAW_GRAPH:
	    /* define the graph corresponding to this window */
	    g = &(win->g);
	    FREE(g->nodes);
	    FREE(g->edges);

	    receive_int_array(&g->nodenum, 1);
	    if ( g->nodenum ) {
	       nodes = g->nodes =
		  (dg_node *) malloc(g->nodenum * sizeof(dg_node));
	       for ( j = 0; j < g->nodenum; j++ ) {
		  read_node_desc_from_pvm(nodes+j, win);
	       }
	    }

	    receive_int_array(&g->edgenum, 1);
	    if ( g->edgenum ) {
	       edges = g->edges =
		  (dg_edge *) malloc(g->edgenum * sizeof(dg_edge));
	       for ( j = 0; j < g->edgenum; j++ ) {
		  read_edge_desc_from_pvm(edges+j, win);
	       }
	    }

	    if ( msgtag == CTOI_SET_AND_DRAW_GRAPH || win->window_displayed )
	       display_graph_on_canvas(win, write_to);

	    break;


	  case CTOI_DRAW_GRAPH:
	    /* first erase/create the window itself, then display all the nodes
	       and edges */
	    display_graph_on_canvas(win, write_to);
	    break;


	  case CTOI_DELETE_GRAPH:
	    /* delete the data structure of the graph and erase its window
	     if open */
	    FREE(win->g.nodes);
	    FREE(win->g.edges);
	    win->g.nodenum = win->g.deleted_nodenum = 0;
	    win->g.edgenum = win->g.deleted_edgenum = 0;
	    if ( win->window_displayed ){
	       spprint(write_to, "Igd_EraseWindow %u\n", win->id);
	    }
	    break;


	  case CTOI_WAIT_FOR_CLICK_NO_REPORT:
	    /* window will not get any messages until the Continue button
	       is pressed. the window has to be open to have an effect */
	    if ( win->window_displayed ) {
	       win->wait_for_click = 1;
	       spprint(write_to, "Igd_CApplWaitForClick %u\n", win->id);
	    } else {
	       INTERMED_ERROR(win->name, msgtag, win->owner_tid,
			      ITOC_WINDOW_ISNT_DISPLAYED);
	    }
	    break;


	  case CTOI_WAIT_FOR_CLICK_AND_REPORT:
	    /* window will not get any messages until the Continue button
	       is pressed. the window has to be open to have an effect.
	       the owner gets a message */
	    if ( win->window_displayed ) {
	       win->wait_for_click = 2;
	       spprint(write_to, "Igd_CApplWaitForClick %u\n", win->id);
	    } else {
	       INTERMED_ERROR(win->name, msgtag, win->owner_tid,
			      ITOC_WINDOW_ISNT_DISPLAYED);
	    }
	    break;


	  case CTOI_SAVE_GRAPH_TO_FILE:
	    /* save the graph into a file (only if it is displayed!) */
	    receive_str(fname);
	    if ( win->window_displayed ) {
	       spprint(write_to, "Igd_SaveGraph %u {%s}\n", win->id, fname);
	    } else {
	       INTERMED_ERROR(win->name, msgtag, win->owner_tid,
			      ITOC_WINDOW_ISNT_DISPLAYED);
	    }
	    break;


	  case CTOI_SAVE_GRAPH_PS_TO_FILE:
	    /* save postscript of the picture displayed. works only if
	       window is displayed. */
	    receive_str(fname);
	    if ( win->window_displayed ) {
	       spprint(write_to, "Igd_SavePs %u {%s}\n", win->id, fname);
	    } else {
	       INTERMED_ERROR(win->name, msgtag, win->owner_tid,
			      ITOC_WINDOW_ISNT_DISPLAYED);
	    }
	    break;


	  case CTOI_CLONE_WINDOW:
	    /* clone this window. if window is not displayed, only the
	     graph data structure will be copied over. */
	    /* wait_for_click, copy_status and text will not be copied over. */
	    receive_str(name2);
	    receive_str(title2);

	    if ( find_window(dgp->window_num, dgp->windows, name2) >= 0 ) {
	       INTERMED_ERROR(win->name, msgtag, sender,
			      ITOC_WINDOW_ALREADY_EXISTS);
	       break;
	    }

	    new_win = init_dgwin(dgp, sender, name2, title2);
	    copy_window_structure(new_win, win);

	    if ( win->window_displayed ) {
	       spprint(write_to,
		       "Igd_CopyWindowDesc %u %u\n", new_win->id, win->id);
	       spprint(write_to,
		       "Igd_InitWindow %u {%s}\n", new_win->id, title2);
	       spprint(write_to, "Igd_DisplayWindow %u\n", new_win->id);
	       spprint(write_to, "Igd_EnableCAppl %u\n", new_win->id);
	       spprint(write_to, "Igd_CopyGraph %u %u\n", new_win->id,win->id);
	       new_win->window_displayed = 1;
	    }
	    break;
	    

	  case CTOI_RENAME_WINDOW:
	    /* change the title of the window */
	    receive_str(win->title);
	    if ( win->window_displayed ){
	       spprint(write_to,
		       "Igd_RenameWindow %u {%s}\n", win->id, win->title);
	    }
	    break;


	  case CTOI_RESIZE_VIEWABLE_WINDOW:
	    /* change the sizes of canvas */
	    receive_int_array(&win->desc.viewable_width, 1);
	    receive_int_array(&win->desc.viewable_height, 1);
	    if ( win->window_displayed ){
	       spprint(write_to, "Igd_ResizeViewableWindow %u %i %i\n",
		       win->id, win->desc.viewable_width,
		       win->desc.viewable_height);
	    }
	    break;


	  case CTOI_RESIZE_CANVAS:
	    /* change the size of the canvas */
	    receive_int_array(&win->desc.canvas_width, 1);
	    receive_int_array(&win->desc.canvas_height, 1);
	    if ( win->window_displayed ){
	       spprint(write_to, "Igd_ResizeCanvas %u %i %i\n", win->id,
		       win->desc.canvas_width, win->desc.canvas_height);
	    }
	    break;


	  case WAITING_TO_GET_A_COPY:
	    /* Read out the name of the source-graph from the pipe.
	       If the source-graph is waiting to be copied, source and
	       target have found each other */
	    receive_str(win->source) ;
	    win->copy_status = 2;

	    j = find_window(dgp->window_num, dgp->windows, win->source);
	    if ( j >= 0 && dgp->windows[j]->copy_status == 1 ) {
	       /* source graph exists and it is waiting to be copied */
	       source_win = dgp->windows[j];

	       /* copy the data structure */
	       copy_window_structure(win, source_win);

	       /* if the window is displayed, change picture */
	       if ( win->window_displayed ) {
		  display_graph_on_canvas(win, write_to);
	       }

	       /* zero out the copy stati */
	       win->copy_status = 0;
	       win->source[0] = 0;
	       source_win->copy_status = 0;
	       source_win->target[0] = 0;
	    }
	    break;


	  case WAITING_TO_BE_COPIED:
	    /* Read out the name of the target graph from the pipe.
	       If the target-graph is waiting to get a copy, source and
	       target have found each other. */
	    receive_str(win->target);
	    win->copy_status = 1;

	    j = find_window(dgp->window_num, dgp->windows, win->target);
	    if ( j >= 0 && dgp->windows[j]->copy_status == 2 ) {
	       /* target exists and waiting for a copy */
	       target_win = dgp->windows[j];

	       /* copy the data structure */
	       copy_window_structure(target_win, win);

	       /* if the target window is displayed, update the picture */
	       if ( target_win->window_displayed ) {
		  display_graph_on_canvas(target_win, write_to);
	       }

	       /* zero out the copy stati */
	       win->copy_status = 0;
	       win->target[0] = 0;
	       target_win->copy_status = 0;
	       target_win->source[0] = 0;
	    }
	    break;
	    

	  case CTOI_MODIFY_GRAPH:
	    /* Make changes in the graph. The data structure is updated,
	       and if the window is displayed, the picture gets updated, too */

	    /* The message is in keyword - description pairs, with the
	       END_OF_MESSAGE keyword at the end. We switch on the keyword */

	    do {
	       receive_int_array(&keyword, 1);

	       switch ( keyword ) {

		case MODIFY_ADD_NODES:
		  /* same format as in SET_GRAPH */
		  receive_int_array(&add_nodenum, 1);
		  if ( add_nodenum ) {
		     g = &(win->g);
		     nodenum = g->nodenum;
		     nodes = g->nodes = (dg_node *)
			realloc(g->nodes,
				(nodenum + add_nodenum) * sizeof(dg_node));
		     for (j = 0, new_nodenum = nodenum; j < add_nodenum; j++) {
			read_node_desc_from_pvm(nodes+new_nodenum, win);
			if (find_node(nodes[new_nodenum].node_id, g) < 0)
			   new_nodenum++;
		     }
		     g->nodenum = new_nodenum;

		     if ( win->window_displayed ) {
			for ( j = nodenum; j < new_nodenum; j++ ) {
			   nod = nodes + j;
			   spprint(write_to,
				   "Igd_MakeNode %u %i %i %i {%s} {%s} %i\n",
				   win->id, nod->node_id, nod->posx,
				   nod->posy, nod->label, nod->dash,
				   nod->radius);
			   if ( *nod->weight != 0 ){
			      spprint(write_to,
				      "Igd_MakeNodeWeight %u %i {%s}\n",
				      win->id, nod->node_id, nod->weight);
			   }
			}
		     }
		  }

		  break;


		case MODIFY_CHANGE_WEIGHTS_OF_NODES:
		  /* change weights of nodes. nodes not in the graph or nodes
		     already deleted are skipped, no error message is given. */
		  g = &(win->g);
		  receive_int_array(&change_nodenum, 1);
		  for ( j = 0; j < change_nodenum; j++ ) {
		     receive_int_array(&node_id, 1);
		     receive_str(new_weight);
		     if ( (k = find_node(node_id, g)) >= 0 ) {
			strcpy(g->nodes[k].weight, new_weight);
			if ( win->window_displayed ) {
			   strcpy(old_weight, g->nodes[k].weight);
			   if ( *old_weight != 0 ) {
			      if ( *new_weight != 0 ) {
				 spprint(write_to,
					 "Igd_ChangeOneNodeWeight %u %i {%s}\n"
					 , win->id, node_id, new_weight);
			      } else {
				 /* new weight == 0 */
				 spprint(write_to,
					 "Igd_DeleteNodeWeight %u %i\n",
					 win->id, node_id);
			      }
			   } else {
			      /* no weight before */
			      if ( *new_weight != 0 ) {
				 spprint(write_to,
					 "Igd_MakeNodeWeight %u %i {%s}\n",
					 win->id, node_id, new_weight);
			      }
			   }
			}
		     }
		  }
		  break;


		case MODIFY_CHANGE_LABELS_OF_NODES:
		  /* change labels of nodes. nodes not in the graph or nodes
		     already deleted are skipped, no error message is given */
		  g = &(win->g);
		  receive_int_array(&change_nodenum, 1);
		  for ( j = 0; j < change_nodenum; j++ ) {
		     receive_int_array(&node_id, 1);
		     receive_str(new_label);
		     if ( (k = find_node(node_id, g)) >= 0 ) {
			strcpy(g->nodes[k].label, new_label);
			if ( win->window_displayed ) {
			   spprint(write_to,
				   "Igd_ChangeOneNodeLabel %u %i {%s}\n",
				   win->id, node_id, new_label);
			}
		     }
		  }
		  break;


		case MODIFY_CHANGE_DASH_OF_NODES:
		  /* change dash pattern of individual nodes. nodes not in the
		     graph will not cause error messages */
		  g = &(win->g);
		  receive_int_array(&change_nodenum, 1);
		  for ( j = 0; j < change_nodenum; j++ ) {
		     receive_int_array(&node_id, 1);
		     receive_str(new_dash);
		     if ( (k = find_node(node_id, g)) >= 0 ) {
			strcpy(g->nodes[k].dash, new_dash);
			if ( win->window_displayed ){
			   spprint(write_to,
				   "Igd_ChangeOneNodeDash %u %i {%s}\n",
				   win->id, node_id, new_dash);
			}
		     }
		  }
		  break;


		case MODIFY_CHANGE_RADII_OF_NODES:
		  /* change radii of individual nodes. nodes not in the
		     graph will not cause error messages */
		  g = &(win->g);
		  receive_int_array(&change_nodenum, 1);
		  for ( j = 0; j < change_nodenum; j++ ) {
		     receive_int_array(&node_id, 1);
		     receive_int_array(&new_radius, 1);
		     if ( (k = find_node(node_id, g)) >= 0 ) {
			g->nodes[k].radius = new_radius;
			if ( win->window_displayed ){
			   spprint(write_to,
				   "Igd_ChangeOneNodeRadius %u %i %i\n",
				   win->id, node_id, new_radius);
			}
		     }
		  }
		  break;


		case MODIFY_DELETE_NODES:
		  /* nodes not in the graph will not cause error messages */
		  receive_int_array(&delete_nodenum, 1);
		  if ( delete_nodenum ) {
		     g = &(win->g);
		     old_deleted_nodenum = g->deleted_nodenum;
		     for ( j = 0; j < delete_nodenum; j++ ) {
			receive_int_array(&node_id, 1);
			if ( (k = find_node(node_id, g)) >= 0 ) {
			   g->nodes[k].deleted = 1;
			   g->deleted_nodenum++;
			   if ( win->window_displayed ){
			      spprint(write_to,
				      "Igd_DeleteNode %u %i\n", win->id,
				      node_id);
			   }
			}
		     }
		     if ( g->deleted_nodenum > old_deleted_nodenum ) { 
			/* mark edges that have at least one deleted endpoint
			   to be deleted. Igd_DeleteNode already took care of
			   deleting these edges from the picture */
			for (k=g->edgenum-1, edg=g->edges; k >= 0; k--, edg++)
			   if ( ! edg->deleted &&
				((find_node(edg->tail, g) < 0) ||
				 (find_node(edg->head, g) < 0))){
			      edg->deleted = 1;
			      g->deleted_edgenum++;
			   }
		     }
		     /* if too many nodes and/or edges have been deleted,
			compress the graph */
		     if ( g->deleted_nodenum > 0.1 * g->nodenum ||
			 g->deleted_edgenum > 0.1 * g->edgenum )
			compress_graph(g);
		  }
		     
		  break;


		case MODIFY_ADD_EDGES:
		  /* same format as in SET_GRAPH. Nonvalid edges (one or
		   both endpoints is not in the graph will not cause an error
		   message. */
		  receive_int_array(&add_edgenum, 1);
		  if ( add_edgenum ) {
		     g = &(win->g);
		     edgenum = g->edgenum;
		     edges = g->edges = (dg_edge *)
			realloc(g->edges,
				(edgenum+add_edgenum)*sizeof(dg_edge));
		     for (j = 0, new_edgenum = edgenum; j < add_edgenum; j++) {
			edg = edges + new_edgenum;
			read_edge_desc_from_pvm(edg, win);
			if ((find_edge(edg->edge_id, g) < 0) &&
			    (find_node(edg->tail, g) >= 0) &&
			    (find_node(edg->head, g) >= 0))
			   new_edgenum++;
		     }
		     g->edgenum = new_edgenum;

		     if ( win->window_displayed ) {
			for ( j = edgenum; j < new_edgenum; j++ ) {
			   edg = edges + j;
			   spprint(write_to, "Igd_MakeEdge %u %i %i %i {%s}\n",
				   win->id, edg->edge_id, edg->tail,
				   edg->head, edg->dash);
			   if ( *edg->weight != 0 ){
			      spprint(write_to,
				      "Igd_MakeEdgeWeight %u %i {%s}\n",
				      win->id, edg->edge_id, edg->weight);
			   }
			}
		     }
		  }

		  break;


		case MODIFY_CHANGE_WEIGHTS_OF_EDGES:
		  /* change weights of edges. edges not in the graph or edges
		     already deleted are skipped, no error message is given. */
		  g = &(win->g);
		  receive_int_array(&change_edgenum, 1);
		  for ( j = 0; j < change_edgenum; j++ ) {
		     receive_int_array(&edge_id, 1);
		     receive_str(new_weight);
		     if ( (k = find_edge(edge_id, g)) >= 0 ) {
			strcpy(g->edges[k].weight, new_weight);
			if ( win->window_displayed ) {
			   strcpy(old_weight, g->edges[k].weight);
			   if ( *old_weight != 0 ) {
			      if ( *new_weight != 0 ) {
				 spprint(write_to,
					 "Igd_ChangeOneEdgeWeight %u %i {%s}\n"
					 , win->id, edge_id, new_weight);
			      } else {
				 /* new weight : 0 */
				 spprint(write_to,
					 "Igd_DeleteEdgeWeight %u %i\n",
					 win->id, edge_id);
			      }
			   } else {
			      /* no weight before */
			      if ( *new_weight != 0 ) {
				 spprint(write_to,
					 "Igd_MakeEdgeWeight %u %i {%s}\n",
					 win->id, edge_id, new_weight);
			      }
			   }
			}
		     }
		  }

		  break;


		case MODIFY_CHANGE_DASH_OF_EDGES:
		  /* change dash pattern of individual edges. edges not in the
		     graph will not cause error messages */
		  g = &(win->g);
		  receive_int_array(&change_edgenum, 1);
		  for ( j = 0; j < change_edgenum; j++ ) {
		     receive_int_array(&edge_id, 1);
		     receive_str(new_dash);
		     if ( (k = find_edge(edge_id, g)) >= 0 ) {
			strcpy(g->edges[k].dash, new_dash);
			if ( win->window_displayed ){
			   spprint(write_to,
				   "Igd_ChangeOneEdgeDash %u %i {%s}\n",
				   win->id, edge_id, new_dash);
			}
		     }
		  }
		  
		  break;


		case MODIFY_DELETE_EDGES:
		  /* edges not in the graph will not cause error messages */
		  g = &(win->g);
		  receive_int_array(&delete_edgenum, 1);
		  for ( j = 0; j < delete_edgenum; j++ ) {
		     receive_int_array(&edge_id, 1);
		     if ( (k = find_edge(edge_id, g)) >= 0 ) {
			g->edges[k].deleted = 1;
			g->deleted_edgenum++;
			if ( win->window_displayed ) {
			   spprint(write_to, "Igd_DeleteEdge %u %i\n",
				   win->id, edge_id);
			}
		     }
		  }
		  /* if too many edges have been deleted, compress the
		     graph */
		  if ( g->deleted_edgenum > 0.1 * g->edgenum )
		     compress_graph(g);
		  
		  break;


		case MODIFY_DELETE_ALL_EDGES:
		  /* will delete all edges from the graph */
		  g = &(win->g);
		  if ( win->window_displayed ) {
		     for ( j = 0; j < g->edgenum; j++ ) 
			if ( ! g->edges[j].deleted ){
			   spprint(write_to, "Igd_DeleteEdge %u %i\n",
				   win->id, g->edges[j].edge_id);
			}
		  }
		  FREE(g->edges);
		  g->edgenum = 0;
		  
		  break;
		  
		case MODIFY_END_OF_MESSAGE:
		  break;
		  
		  
		default:
		  printf("Unrecognized keyword %i\n", keyword);
		  break;
		  
		  
	       } /* end switch (keyword) */
	       
	    } while ( keyword != MODIFY_END_OF_MESSAGE );

	    break;


	  case CTOI_CLEAR_MESSAGE:
	    if ( win->window_displayed ) {
	       spprint(write_to, "Igd_CApplClearCmsg %u\n", win->id);
	    }
	    break;

	  case CTOI_PRINT_MESSAGE:
	    if ( win->window_displayed ) {
	       str = malloc(bytes);
	       receive_str(str);
	       spprint(write_to, "Igd_CApplSetCmsg %u {%s}\n", win->id, str);
	       FREE(str);
	    }
	    break;

	  case CTOI_APPEND_MESSAGE:
	    if ( win->window_displayed ) {
	       str = malloc(bytes);
	       receive_str(str);
	       spprint(write_to, "Igd_CApplAppendCmsg %u {%s}\n", win->id,str);
	       FREE(str);
	    }
	    break;

	  default:
	    printf("Unknown message tag: %i\n", msgtag);
	    break;

	 } /* end switch (msgtag) */

	 freebuf(r_bufid);
      } /* end for */
      
   } /* end while */
   return(0);
}


/*===========================================================================*/

/*===========================================================================*\
 * Find the window with the given name in windows.
\*===========================================================================*/

int find_window(int window_num, window **windows, char *name)
{
   int i;

   for ( i = window_num - 1; i >= 0; i-- )
      if ( strcmp(windows[i]->name, name) == 0 )
	 break;

   return(i);
}

/*===========================================================================*/

/*===========================================================================*\
 * Read out the description of a node from pvm buffer 
\*===========================================================================*/

void read_node_desc_from_pvm(dg_node *nod, window *win)
{
   int key;

   receive_int_array(&nod->node_id, 1);
   receive_int_array(&nod->posx, 1);
   receive_int_array(&nod->posy, 1);
   receive_int_array(&key, 1);

   if ( key & 0x08 ){
      receive_str(nod->weight);
   }else{
      *nod->weight = 0;
   }
   if ( key & 0x04 ) {
      receive_str(nod->label);
   } else {
      sprintf(nod->label, "%i", nod->node_id);
   }
   if ( key & 0x02 ) {
      receive_str(nod->dash);
   } else {
      strcpy(nod->dash, win->desc.node_dash);
   }
   if ( key & 0x01 ) {
      receive_int_array(&nod->radius, 1);
   } else {
      nod->radius = win->desc.node_radius;
   }
   nod->deleted = FALSE;
}

/*===========================================================================*/

/*===========================================================================*\
 * Read out the description of an edge from pvm buffer
\*===========================================================================*/

void read_edge_desc_from_pvm(dg_edge *edg, window *win)
{
   int key;

   receive_int_array(&edg->edge_id, 1);
   receive_int_array(&edg->tail, 1);
   receive_int_array(&edg->head, 1);
   receive_int_array(&key, 1);
   if ( key & 0x08 ){
      receive_str(edg->weight);
   }else{
      *edg->weight = 0;
   }
   if ( key & 0x02 ) {
      receive_str(edg->dash);
   } else {
      strcpy(edg->dash, win->desc.edge_dash);
   }
   edg->deleted = FALSE;
}

/*===========================================================================*/

/*===========================================================================*\
 * Find the index of node with node_id in the graph.
\*===========================================================================*/

int find_node(int node_id, dg_graph *g)
{
   int i;

   for ( i = g->nodenum-1; i >= 0; i-- )
      if ( g->nodes[i].node_id == node_id )
	 break;

   if ( i >= 0 && ! g->nodes[i].deleted ) {
      return(i);
   } else {
      return(-1);
   }

   return(-1);
}

/*===========================================================================*/

/*===========================================================================*\
 * Find the index of edge with edge_id in the graph.
\*===========================================================================*/

int find_edge(int edge_id, dg_graph *g)
{
   int i;

   for ( i = g->edgenum-1; i >= 0; i-- )
      if ( g->edges[i].edge_id == edge_id )
	 break;

   if ( i >= 0 && ! g->edges[i].deleted ) {
      return(i);
   } else {
      return(-1);
   }

   return(-1);
}

/*===========================================================================*/

/*===========================================================================*\
 * Compess the graph: delete nodes and edges that have been marked.
\*===========================================================================*/

void compress_graph(dg_graph *g)
{
   dg_node *nodes = g->nodes;
   dg_edge *edges = g->edges;
   int new_nodenum, new_edgenum;
   int i;

   if ( g->deleted_nodenum ) {
      /* find the first deleted node */
      for ( i = 0; i < g->nodenum; i++ ) {
	 if ( nodes[i].deleted )
	    break;
      }
      
      for ( new_nodenum = i; i < g->nodenum; i++ ) {
	 if ( ! nodes[i].deleted ) 
	    nodes[new_nodenum++] = nodes[i];
	    
      }

      g->nodes = (dg_node *) realloc(nodes, new_nodenum * sizeof(dg_node));
      g->nodenum = new_nodenum;
      g->deleted_nodenum = 0;
   }

   if ( g->deleted_edgenum ) {
      /* find the first deleted edge */
      for ( i = 0; i < g->edgenum; i++ ) {
	 if ( edges[i].deleted )
	    break;
      }
      
      for ( new_edgenum = i; i < g->edgenum; i++ ) {
	 if ( ! edges[i].deleted ) 
	    edges[new_edgenum++] = edges[i];
	    
      }

      g->edges = (dg_edge *) realloc(edges, new_edgenum * sizeof(dg_edge));
      g->edgenum = new_edgenum;
      g->deleted_edgenum = 0;
   }
   
}
   
/*===========================================================================*/

/*===========================================================================*\
 * Copy the source window into target window's structure.
 * The following will be copied over: desc and g.
 * It is assumed that space is already allocated for the target_window.
\*===========================================================================*/

void copy_window_structure(window *target_win, window *source_win)
{
   int nodenum = source_win->g.nodenum;
   int edgenum = source_win->g.edgenum;

   target_win->desc = source_win->desc;

   FREE(target_win->g.nodes);
   FREE(target_win->g.edges);
   
   if ( (target_win->g.nodenum = nodenum) ) {
      target_win->g.nodes = (dg_node *) malloc(nodenum * sizeof(dg_node));
      memcpy(target_win->g.nodes, source_win->g.nodes,
	     nodenum * sizeof(dg_node));
   }

   if ( (target_win->g.edgenum = edgenum) ) {
      target_win->g.edges = (dg_edge *) malloc(edgenum * sizeof(dg_edge));
      memcpy(target_win->g.edges, source_win->g.edges,
	     edgenum * sizeof(dg_edge));
   }
}
      
/*===========================================================================*/

/*===========================================================================*\
 * Display the graph in window's data structure on the canvas.
 * write_to is teh handle to wish.
\*===========================================================================*/

void display_graph_on_canvas(window *win, FILE *write_to)
{
   win_desc *desc = &(win->desc);
   dg_graph *g = &(win->g);
   int j;
   dg_node *nod;
   dg_edge *edg;

   if ( win->window_displayed ) {
      
      /* need to erase the window then reset the window descriptions */
      spprint(write_to, "Igd_EraseWindow %u\n", win->id);
      spprint(write_to, "Igd_SetAndExecuteWindowDesc %u %i %i %i %i %i %i %i {%s} {%s} %i %i %i %f %s %s %s\n",
	      win->id, desc->canvas_width, desc->canvas_height,
	      desc->viewable_width, desc->viewable_height,
	      desc->disp_nodelabels, desc->disp_nodeweights,
	      desc->disp_edgeweights, desc->node_dash, desc->edge_dash,
	      desc->node_radius, desc->interactive_mode,
	      desc->mouse_tracking, desc->scale_factor, desc->nodelabel_font,
	      desc->nodeweight_font, desc->edgeweight_font);
      
   } else {

      /* create window and set window description */
      spprint(write_to, "Igd_SetWindowDesc %u %i %i %i %i %i %i %i {%s} {%s} %i %i %i %f %s %s %s\n",
	      win->id, desc->canvas_width, desc->canvas_height,
	      desc->viewable_width, desc->viewable_height,
	      desc->disp_nodelabels, desc->disp_nodeweights,
	      desc->disp_edgeweights, desc->node_dash, desc->edge_dash,
	      desc->node_radius, desc->interactive_mode,
	      desc->mouse_tracking, desc->scale_factor, desc->nodelabel_font,
	      desc->nodeweight_font, desc->edgeweight_font);
      spprint(write_to, "Igd_InitWindow %u {%s}\n", win->id, win->title);
      spprint(write_to, "Igd_DisplayWindow %u\n", win->id);
      spprint(write_to, "Igd_EnableCAppl %u\n", win->id);
      win->window_displayed = 1;
   }

   /* now display the nodes and edges */

   if ( g->nodenum ) {
      for ( j = 0; j < g->nodenum; j++ ) {
	 nod = g->nodes + j;
	 if ( !nod->deleted ) {
	    spprint(write_to, "Igd_MakeNode %u %i %i %i %s {%s} %i\n",
		    win->id, nod->node_id, nod->posx, nod->posy,
		    nod->label, nod->dash, nod->radius);
	    if ( *nod->weight != 0 ){
	       spprint(write_to, "Igd_MakeNodeWeight %u %i %s\n",
		       win->id, nod->node_id, nod->weight);
	    }
	 }
      } /* endfor j */
   }
   if ( g->edgenum ) {
      for ( j = 0; j < g->edgenum; j++ ) {
	 edg = g->edges + j;
	 if ( !edg->deleted ) {
	    spprint(write_to, "Igd_MakeEdge %u %i %i %i {%s}\n",
		    win->id, edg->edge_id, edg->tail, edg->head,
		    edg->dash);
	    if ( *edg->weight != 0 ){
	       spprint(write_to, "Igd_MakeEdgeWeight %u %i {%s}\n",
		       win->id, edg->edge_id, edg->weight);
	    }
	 }
      } /* endfor j */
   }
}

/*===========================================================================*/

/*===========================================================================*\
 * Disassemble data structure windows[i].
\*===========================================================================*/

void free_window(int *pwindow_num, window **windows, int i)
{
   window *w = windows[i];

   FREE(w->g.nodes);
   FREE(w->g.edges);
   /* free the bufid fifo */
   FREE(w->buf.bufid);
   if (w->user){
#ifdef USE_SYM_APPLICATION
      user_dg_free_window(&w->user, w);
#else
      FREE(w->user);
#endif
   }
   FREE(w);

   /* delete pointer from windows */
   if ( i < *pwindow_num - 1 )
      windows[i] = windows[*pwindow_num-1];
   (*pwindow_num)--;
}   

/*===========================================================================*/

void copy_win_desc_from_par(window *win, dg_params *par)
{
   win->desc.canvas_width = par->canvas_width;
   win->desc.canvas_height = par->canvas_height;
   win->desc.viewable_width = par->viewable_width;
   win->desc.viewable_height = par->viewable_height;

   win->desc.disp_nodelabels = par->disp_nodelabels;
   win->desc.disp_nodeweights = par->disp_nodeweights;
   win->desc.disp_edgeweights = par->disp_edgeweights;

   strcpy(win->desc.node_dash, par->node_dash);
   strcpy(win->desc.edge_dash, par->edge_dash);

   win->desc.node_radius = par->node_radius;
   win->desc.interactive_mode = par->interactive_mode;
   win->desc.mouse_tracking = par->mouse_tracking;
   win->desc.scale_factor = par->scale_factor;
   
   strcpy(win->desc.nodelabel_font, par->nodelabel_font);
   strcpy(win->desc.nodeweight_font, par->nodeweight_font);
   strcpy(win->desc.edgeweight_font, par->edgeweight_font);
}

/*===========================================================================*/

void set_window_desc_pvm(int key, window *win)
{
   win_desc *desc = &win->desc;

   switch ( key ) {
    case CANVAS_WIDTH:
      receive_int_array(&desc->canvas_width, 1);
      break;
    case CANVAS_HEIGHT:
      receive_int_array(&desc->canvas_height, 1);
      break;
    case VIEWABLE_WIDTH:
      receive_int_array(&desc->viewable_width, 1);
      break;
    case VIEWABLE_HEIGHT:
      receive_int_array(&desc->viewable_height, 1);
      break;
    case DISP_NODELABELS:
      receive_int_array(&desc->disp_nodelabels, 1);
      break;
    case DISP_NODEWEIGHTS:
      receive_int_array(&desc->disp_nodeweights, 1);
      break;
    case DISP_EDGEWEIGHTS:
      receive_int_array(&desc->disp_edgeweights, 1);
      break;
    case NODE_DASH:
      receive_str(desc->node_dash);
      break;
    case EDGE_DASH:
      receive_str(desc->edge_dash);
      break;
    case NODE_RADIUS:
      receive_int_array(&desc->node_radius, 1);
      break;
    case INTERACTIVE_MODE:
      receive_int_array(&desc->interactive_mode, 1);
      break;
    case MOUSE_TRACKING:
      receive_int_array(&desc->mouse_tracking, 1);
      break;
    case SCALE_FACTOR:
      receive_dbl_array(&desc->scale_factor, 1);
      break;
    case NODELABEL_FONT:
      receive_str(desc->nodelabel_font);
      break;
    case NODEWEIGHT_FONT:
      receive_str(desc->nodeweight_font);
      break;
    case EDGEWEIGHT_FONT:
      receive_str(desc->edgeweight_font);
      break;
   }
}

/*===========================================================================*/

void wait_for_you_can_die(dg_prob *dgp, FILE *write_to)
{
   int bufid, s_bufid, bytes, msgtag, sender;

   FREE(dgp->windows);
   /* invoke the Igd_QuitAll function */
   spprint(write_to, "Igd_QuitAll\n");

   if (dgp->waiting_to_die == 2 * TRUE)
      exit(0);

   while (TRUE){
      receive_msg(ANYONE, ANYTHING);
      bufinfo(bufid, &bytes, &msgtag, &sender);
      if (msgtag != CTOI_YOU_CAN_DIE){
	 s_bufid = init_send(DataInPlace);
	 send_msg(sender, ITOC_APPLICATION_KILLED);
	 freebuf(s_bufid);
      }else{
	 exit(0);
      }
   }
}

/*===========================================================================*/

window *init_dgwin(dg_prob *dgp, int sender, char *name, char *title)
{
   window *win = (window *) calloc(1, sizeof(window));

   win->owner_tid = sender;
   strcpy(win->name, name);
   strcpy(win->title, title);
   win->id = dgp->next_id++;
   /* initialize buf_fifo */
   win->buf.bufid = (int *) malloc(127 * ISIZE);
   win->buf.bufspace = 127;
   win->buf.bufread = -1;
   win->buf.bufwrite = 0;

   dgp->window_num++;
   if (dgp->window_num == 1)
      dgp->windows = (window **) malloc( sizeof(window *) );
   else
      dgp->windows = (window **)
	 realloc(dgp->windows, dgp->window_num * sizeof(window *));
   dgp->windows[dgp->window_num-1] = win;
#ifdef USE_SYM_APPLICATION
   CALL_USER_FUNCTION( user_dg_init_window(&win->user, win) );
#else
   win->user = NULL;
#endif
   return(win);
}

/*===========================================================================*/

void add_msg(window *win, int bufid)
{
   register buf_fifo *buf = &win->buf;

   if (buf->bufread == -1){
      /* then bufwrite must be 0 */
      buf->bufid[0] = bufid;
      buf->bufread = 0;
      buf->bufwrite = 1;
      return;
   }
   if (buf->bufread == buf->bufwrite){
      /* the list of bufid's is full */
      int *newbufid  = (int *) malloc((buf->bufspace + 128) * ISIZE);
      memcpy(newbufid, buf->bufid + buf->bufread,
	     (buf->bufspace - buf->bufread) * ISIZE);
      memcpy(newbufid + (buf->bufspace - buf->bufread), buf->bufid,
	     buf->bufread * ISIZE);
      FREE(buf->bufid);
      buf->bufid = newbufid;
      buf->bufread = 0;
      buf->bufwrite = buf->bufspace;
      buf->bufspace += 128;
   }
   buf->bufid[buf->bufwrite] = bufid;
   if (++buf->bufwrite == buf->bufspace)
      buf->bufwrite = 0;
}

/*===========================================================================*/

int get_next_msg(window *win)
{
   register buf_fifo *buf = &win->buf;
   int bufid = buf->bufid[buf->bufread];

   if (++buf->bufread == buf->bufspace)
      buf->bufread = 0;
   if (buf->bufread == buf->bufwrite){
      buf->bufread = -1;
      buf->bufwrite = 0;
   }
   return( bufid );
}



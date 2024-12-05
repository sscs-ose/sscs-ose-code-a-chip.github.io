#include <stdio.h>
#include <fcntl.h>
#include <unistd.h>


int start_child(char *cmd, FILE **readpipe, FILE **writepipe);


void main(int argc, char **argv)
{
   char *source_path = "/home/tkr/SYMPHONY/DrawGraph/IGD_1.0/";
   char *graph_name = NULL;
   FILE *read_from, *write_to;
   int childpid;

   if (argc > 1)
      graph_name = argv[1];

   /* fork the wish shell */
   childpid = start_child((char *)"wish", &read_from, &write_to);
      
   /* source the tcl script into wish and invoke Igd_StartUp */
   fprintf(write_to, "source %s/Init.tcl\n", source_path);
   fprintf(write_to, "source %s/Tools.tcl\n", source_path);
   fprintf(write_to, "source %s/NodeEdgeBasics.tcl\n", source_path);
   fprintf(write_to, "source %s/FileMenu.tcl\n", source_path);
   fprintf(write_to, "source %s/WindowMenu.tcl\n", source_path);
   fprintf(write_to, "source %s/NodeMenu.tcl\n", source_path);
   fprintf(write_to, "source %s/EdgeMenu.tcl\n", source_path);
   fprintf(write_to, "Igd_StartUp\n");
   fprintf(write_to, "Igd_CopyApplDefaultToWindow 1\n");
   fprintf(write_to, "Igd_InitWindow 1 first\n");
   fprintf(write_to, "Igd_DisplayWindow 1\n");
   if (graph_name)
      fprintf(write_to, "Igd_LoadGraph 1 %s\n", graph_name);
}


/*****************************************************************************
 * Exec the named cmd as a child process, returning two pipes to
 * communicate with the process, and the child's process ID.
 *****************************************************************************/

int start_child(char *cmd, FILE **readpipe, FILE **writepipe)
{
   int childpid, pipe1[2], pipe2[2];

   if ((pipe(pipe1) < 0) || (pipe(pipe2) < 0)){
      perror("pipe");
      exit(-1);
   }

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
   return(0);
}

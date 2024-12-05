#include "flopc.hpp"
using namespace flopc;
#include "OsiSymSolverInterface.hpp"

/* Teacher Assignment Problem

T. H. Hultberg and D. M. Cardoso, "The teacher assignment problem: A special 
case of the fixed charge transportation problem", European Journal of 
Operational Research, 101(3):463-474,1997.
*/

class Tap : public MP_model {
public:
    MP_set S,D;
    MP_data s;
    MP_data d;
    MP_variable x;
    MP_variable y;  
    MP_constraint supply, demand, def_y;

    Tap(int numS, int numD) : MP_model(new OsiSymSolverInterface),
			      S(numS), D(numD),
			      s(S), d(D),
			      x(S,D), y(S,D),
			      supply(S), demand(D), def_y(S,D) {
	y.binary();
	
	supply(S) = sum(D, x(S,D)) <= s(S);
	
	demand(D) = sum(S, x(S,D)) >= d(D) ; 
	
	def_y(S,D) = d(D)*y(S,D) >= x(S,D);
	
	add(supply); add(demand); add(def_y);
	
	setObjective( sum(S*D, y(S,D)) );
	
    }    
};

main() {
    double stab_1[6]  = {5,5,6,6,6,6};
    double dtab_1[4]  = {4, 7, 10, 11};
    double stab_2[7] =  {9,9,10,12,12,12,16};
    double dtab_2[5] =  {6, 14, 17, 21, 22};
    
    Tap first_instance(6,4);
    Tap second_instance(7,5);

    first_instance.s.value(stab_1);
    first_instance.d.value(dtab_1);

    second_instance.s.value(stab_2);
    second_instance.d.value(dtab_2);
        
    first_instance.minimize();
    first_instance.x.display("Solution of first instance (x)");
    first_instance.y.display("Solution of first instance (y)");

    second_instance.minimize();
    second_instance.x.display("Solution of second instance");
}

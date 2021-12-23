
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTIBILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from .maintool_default import MainToolDefault
from .maintool_hold import MainToolHold
from .maintool_brush import *
from .maintool_lowpoly import MainToolLowPoly
from .maintool_knife import MainToolKnife
from .maintool_delete import MainToolDelete
from .maintool_extrude import MainToolExtrude
from .maintool_loopcut import MainToolLoopCut
from .maintool_edgeloop import MainToolEdgeLoop
from .maintool_edgeloop_dissolve import MainToolEdgeLoopDissolve
from .subtool_edgeloop_extrude import SubToolEdgeLoopExtrude
from .subtool_seam import SubToolSeam
from .subtool_seam_loop import SubToolSeamLoop
from .maintool_quad_patch import MainToolQuadPatch

maintools = {
    'NONE'              : None ,
    'MASTER'            : MainToolDefault ,
#   'HOLD'              : MainToolHold ,
    'LOWPOLY'           : MainToolLowPoly ,
    'BRUSH'             : MainToolBrush ,
    'EXTRUDE'           : MainToolExtrude ,
    'KNIFE'             : MainToolKnife ,
    'DELETE'            : MainToolDelete ,
    'EDGELOOP'          : MainToolEdgeLoop ,
    'LOOPCUT'           : MainToolLoopCut ,
    'EDGELOOP_EXTRUDE'  : SubToolEdgeLoopExtrude ,
    'EDGELOOP_DISSOLVE' : MainToolEdgeLoopDissolve ,
    'MARK_SEAM'         : SubToolSeam ,
    'MARK_SEAM_LOOP'    : SubToolSeamLoop ,
    'QUADPATCH'         : MainToolQuadPatch ,
}

def enum_tool_callback(scene, context ):
    return ( ( tool , cls.name if cls else "None" , "" ,"", index  ) for index , (tool,cls) in enumerate(maintools.items()) )
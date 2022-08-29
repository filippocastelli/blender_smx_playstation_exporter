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
import bpy
from .blender_smx_exporter import ExportPSX

bl_info = {
    "name" : "PlayStation SMX Exporter",
    "author" : "afire101",
    "description" : "Export mesh to SMX model format",
    "blender" : (3, 2, 0),
    "version" : (0, 0, 1),
    "location": "File > Import-Export",
    "warning" : "",
    "category": "Import-Export",
}

def menu_func_export(self, context):
    self.layout.operator(ExportPSX.bl_idname, text="PlayStation SMX Format(.smx)")
    
def register():
    bpy.utils.register_class(ExportPSX)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)

def unregister():
    bpy.utils.unregister_class(ExportPSX)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)

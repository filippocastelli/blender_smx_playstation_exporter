bl_info = {
    "name": "PlayStation SMX exporter",
    "author": "afire101, Lameguy64",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "Export mesh to SMX model format",
    "description": "asd",
    "warning": "",
    "category": "Export Plugin",
}
from pathlib import Path
import typing

import bpy

from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import Operator

class ExportPSX(Operator, ExportHelper):
    bl_idname = "export_smx.smx"
    bl_label = "Export SMX"
    filename_ext = ".smx"
    filter_glob = StringProperty(default="*.smx", options={"HIDDEN"})
    bl_options = {
        "PRESET",
    }
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    check_extension = False
    
    # export props
    exp_applyModifiers: BoolProperty(
        name="Apply Modifiers",
        description="Apply modifiers before exporting",
        default=True
    )
    
    exp_writeNormals: BoolProperty(
        name="Write Normals",
        description="Write normals for smooth and hard shaded faces",
        default=True
    )
    
    
    @classmethod
    def triangulate_mesh(mesh: bpy.types.Mesh) -> None:
        for poly in mesh.polygons:
            if len(poly.vertices) > 4:
                pass        
        
    @staticmethod
    def apply_modifiers(obj) -> None:
        for modifier in obj.modifiers:
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        
    @staticmethod
    def _write_verts(f: typing.TextIO, mesh: bpy.types.Mesh) -> list:
        f.write("\t<vertices count=\"%d\">\n" % len(mesh.vertices))
        for v in mesh.vertices:
            f.write("\t\t<v x=\"%f\" y=\"%f\" z=\"%f\"/>\n" % (v.co.x, -v.co.z, v.co.y))
        f.write("\t</vertices>\n")
        
        return mesh.vertices
        
    @staticmethod
    def _write_normals(f: typing.TextIO, mesh: bpy.types.Mesh) -> typing.Tuple[list, list]:
        # check if there are any flat primitives
        has_flats = any(tri.use_smooth is False for tri in mesh.loop_triangles)
        
        smooth_normals = [(v.normal.x, -v.normal.z, v.normal.y) for v in mesh.vertices]
        flat_normals = [(p.normal.x, -p.normal.z, p.normal.y) for p in mesh.polygons] if has_flats else []
        
        normals_count = len(flat_normals) + len(smooth_normals) if has_flats else len(smooth_normals)
        
        f.write(f"\t<normals count=\"{normals_count}\">\n")
        f.write("\t\t<!-- Smooth normals begin here -->\n")
        for smooth_norm in smooth_normals:
            f.write(f"\t\t<v x=\"{smooth_norm[0]}\" y=\"{smooth_norm[1]}\" z=\"{smooth_norm[2]}\"/>\n")
        
        if has_flats:
            f.write("\t\t<!-- Flat normals begin here -->\n")
            for flat_norm in flat_normals:
                f.write(f"\t\t<v x=\"{flat_norm[0]}\" y=\"{flat_norm[1]}\" z=\"{flat_norm[2]}\"/>\n")
                
        f.write("\t</normals>\n")
        return (smooth_normals, flat_normals)
    
    @classmethod
    def _write_textures(cls, f: typing.TextIO, mesh: bpy.types.Mesh, node_type: str = "BSDF_DIFFUSE") -> typing.List[str]:
        """create texture tags"""
        textures = cls._get_mesh_textures(mesh, node_type=node_type)
        if len(textures) > 0:
            f.write(f"\t<textures count=\"{len(textures)}\">\n")
            for textr in textures:
                textr_stem = Path(textr.name).stem
                f.write(f"\t\t<texture file=\"{textr_stem}\">\n")
            f.write("\t</textures>\n")
            
        return textures
                
    @classmethod
    def _get_mesh_textures(cls, mesh: bpy.types.Mesh, node_type: str = "BSDF_DIFFUSE") -> typing.List[bpy.types.Image]:
        """return list of texture bpy.Image """
        textures = []
        
        for mat in mesh.materials:
            text = cls._get_mat_texture(mat, node_type=node_type)
            if text is not None:
                textures.append(text)
        
        return textures
    
    @staticmethod
    def _get_mat_texture(mat: bpy.types.Material, node_type: str = "BSDF_DIFFUSE") -> bpy.types.Image:
        """get material's texture"""
        # for supported materials see RSD Exporter example blend
        try:
            nodes = mat.node_tree.nodes
            matnode = next(node for node in nodes if node.type in ["BSDF_DIFFUSE", "EMISSION"])
            color_input = matnode.inputs["Color"]
            
            if color_input.links[0].from_node.type == "MIX_RGB":
                # textured and vertex colored, mixed
                mix_rgb_node = color_input.links[0].from_node
                color_inputs = [node for node in mix_rgb_node.inputs if "Color" in node.name]
                link = next(col_input.links[0].from_node for col_input in color_inputs if hasattr(col_input.links[0].from_node,"image"))
            else:
                # simple texture input
                link = color_input.links[0].from_node
            img = link.image
            return img
        except:
            return None
    
    @classmethod
    def _write_primitives(cls, f: typing.TextIO, obj:bpy.types.Object, textures:list) -> list:
        """populate primitive tags"""
        polys = obj.data.polygons
        primitives = []
        f.write("\t<primitives count=\"%d\">\n" % len(polys))
        for poly_idx, poly in enumerate(polys):
            primitive_str = cls._get_primitive_str(idx=poly_idx, poly=poly, textures=textures)
            primitives.append(primitive_str)
            f.write("\t\t"+primitive_str+"\n")
        f.write("\t</primitives>\n")
    
    @classmethod
    def _get_primitive_str(cls,
                    idx: int,
                    poly: bpy.types.MeshPolygon,
                    textures: list) -> str:
        """return SMX format primitive entry str

        Args:
            idx (int): primitive index
            poly (bpy.types.MeshPolygon): primitive poly
            textures (list): list of model's textures

        Returns:
            str: primitive index str
        """
        id_data = poly.id_data
        
        material_index = poly.material_index
        mat = id_data.materials[material_index]
        texture_name = cls._get_mat_texture(mat)
        if texture_name is not None:
            texture_idx = textures.index(texture_name) if texture_name in textures else -1
            assert texture_idx >= 0, f"Texture {texture_name} not found in textures list"
        else: texture_idx = None
            
        n_poly_verts = len(poly.vertices)
        
        #shading
        if n_poly_verts == 3:
            poly_type = "triangle"
            verts = [poly.vertices[i] for i in [0,2,1]]
        elif n_poly_verts == 4:
            poly_type = "quad"
            verts = [poly.vertices[i] for i in [3,2,0,1]]
        if poly.use_smooth:
            shading="S"
            norms = verts
        else:
            shading="F"
            flatnorms_start = len(poly.id_data.vertices)
            norms = [flatnorms_start+idx]
        
        # colors
        has_colors = len(id_data.color_attributes) > 0
        color_multiplier = 255.0 if len(textures)>0 else 128.0
        # typecode in "F" for flat, "G" for gouraud
        colors = []
        if has_colors:
            colorattr = id_data.color_attributes[0]
            for vert_idx in poly.loop_indices:
                r,g,b,a = colorattr.data[vert_idx].color
                scale_color = lambda color: color*color_multiplier
                color = [r,g,b]
                color = map(scale_color, color)
                color = list(map(int, color))
                colors.append(color)
                
            if colors.count(colors[0]) == len(colors):
                typecode = "F" # is flat
            else:
                typecode = "G" # is gouraud
        else:
            colors = [(128, 128, 128)]
            typecode = "F" # automatically flat 

        # uv map
        uvs = []
        if texture_idx is not None:
            uv_layer = id_data.uv_layers.active
            for vert_idx in poly.loop_indices:
                uv = uv_layer.data[vert_idx].uv
                uvs.append((uv[0], uv[1]))
            typecode += "T" # has texture
        else:
            pass
        
        typecode += str(n_poly_verts) # "FT3"
        
        # writing to file
        # vertices
        vert_strlist = [f"v{ax}=\"{vert}\"" for ax, vert in enumerate(verts)] # v0="0" v1="1" v2="2"
        
        # normals
        norm_strlist = [f"n{ax}=\"{norm}\"" for ax, norm in enumerate(norms)] # n0="0" n1="1" n2="2"
        
        # colors
        col_tuple2strlist = lambda coltuple, vert_idx: [f"r{vert_idx}=\"{coltuple[0]}\"", f"g{vert_idx}=\"{coltuple[1]}\"", f"b{vert_idx}=\"{coltuple[2]}\""] # r0="128" g0="128" b0="128"
        col_strlist = [col_tuple2strlist(col, vert_idx) for col, vert_idx in zip(colors, range(n_poly_verts))] # [["r0","g0","b0"],["r1","g1","b1"],["r2","g2","b2"]]
        col_strlist = [item for sublist in col_strlist for item in sublist] # ["r0","g0","b0","r1","g1","b1","r2","g2","b2"]
        
        # uv
        uv_tuple2strlist = lambda uvtuple, vert_idx: [f"tu{vert_idx}=\"{uvtuple[0]}\"", f"tv{vert_idx}=\"{uvtuple[1]}\""] # tu0="0" tv0="0"
        uv_strlist = [uv_tuple2strlist(uv, vert_idx) for uv, vert_idx in zip(uvs, range(n_poly_verts))] # [["tu0","tv0"],["tu1","tv1"],["tu2","tv2"]]
        uv_strlist = [uvstring for uvlist in uv_strlist for uvstring in uvlist] # ["tu0","tv0","tu1","tv1","tu2","tv2"]
        
        texture_strlist = [f"texture=\"{texture_idx}\"",] if texture_idx is not None else []
        prim_strlist = ["<poly",
                        *vert_strlist,
                        *norm_strlist,
                        f"shading=\"{shading}\"",
                        *col_strlist,
                        *texture_strlist,
                        *uv_strlist,
                        f"type=\"{typecode}\"",
                        "\"/>"]
        prim_str = " ".join(prim_strlist)
        
        return prim_str
    
    def invoke(self, context, _event):
        # override invoke method to to use selected object's name as default
        if not self.filepath:
            self.filepath = context.object.name + self.filename_ext
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}
        
    def execute(self, context):
        # active object
        obj = bpy.context.object
        
        if self.exp_applyModifiers:
            self.apply_modifiers(obj)
            
        mesh = obj.to_mesh(preserve_all_data_layers=True)
        
        if len(mesh.loop_triangles) == 0:
            mesh.calc_loop_triangles()
        
        filepath = self.filepath
        filepath = bpy.path.ensure_ext(filepath, self.filename_ext)
        self.pathlib_filepath = Path(filepath)
        
        with self.pathlib_filepath.open(mode="w") as f:
            f.write("<!-- Created using SMX Export Plug-in for Blender -->\n")
            f.write("<!-- Rewrite by afire101, based on original from Lameguy64 -->\n")
            f.write("<!-- NOTE: If you plan to use this model as a static mesh, it is recommended that you run this file through smxopt -->\n")
            f.write("<!-- or smxtool to clean up duplicate/unused normals which are kept for animation purposes. -->\n")
            f.write("<model version=\"1\">\n")
            # write vertices
            verts = self._write_verts(f, mesh)
            
            # write normals
            norms = ()
            if self.exp_writeNormals:
                norms = self._write_normals(f, mesh)

            # write textures
            textures = self._write_textures(f, mesh, node_type="BSDF_DIFFUSE")
            
            # write primitives
            primitives = self._write_primitives(f=f, obj=obj, textures=textures)
            
            f.write("</model>")
        return {"FINISHED"}

def menu_func_export(self, context):
    self.layout.operator(ExportPSX.bl_idname,  text="PSX Format(.c)")
    
def register():
    bpy.utils.register_class(ExportPSX)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    
def unregister():
    bpy.utils.unregister_class(ExportPSX)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
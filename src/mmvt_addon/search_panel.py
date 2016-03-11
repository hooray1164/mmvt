import bpy
import mmvt_utils as mu


class SearchFilter(bpy.types.Operator):
    bl_idname = "ohad.selection_filter"
    bl_label = "selection filter"
    bl_options = {"UNDO"}
    marked_objects_select = {}

    def invoke(self, context, event=None):
        label_name = context.scene.labels_regex
        SearchMark.marked_objects_select = {}
        objects = mu.get_non_functional_objects()
        for obj in objects:
            SearchFilter.marked_objects_select[obj.name] = obj.select
            obj.select = label_name in obj.name
        SearchPanel.addon.show_rois()
        return {"FINISHED"}


class SearchClear(bpy.types.Operator):
    bl_idname = "ohad.selection_clear"
    bl_label = "selection clear"
    bl_options = {"UNDO"}

    def invoke(self, context, event=None):
        # Copy from where am I clear
        for subHierchy in bpy.data.objects['Brain'].children:
            new_mat = bpy.data.materials['unselected_label_Mat_cortex']
            if subHierchy.name == 'Subcortical_structures':
                new_mat = bpy.data.materials['unselected_label_Mat_subcortical']
            for obj in subHierchy.children:
                 obj.active_material = new_mat

        for obj in bpy.data.objects['Deep_electrodes'].children:
            obj.active_material.node_tree.nodes["Layer Weight"].inputs[0].default_value = 1

        for obj_name, h in SearchMark.marked_objects_hide.items():
            bpy.data.objects[obj_name].hide = bool(h)
        for obj_name, h in SearchFilter.marked_objects_select.items():
            # print('bpy.data.objects[{}].select = {}'.format(obj_name, bool(h)))
            bpy.data.objects[obj_name].select = bool(h)
        return {"FINISHED"}


class SearchMark(bpy.types.Operator):
    bl_idname = "ohad.selection_mark"
    bl_label = "selection mark"
    bl_options = {"UNDO"}
    marked_objects_hide = {}

    def invoke(self, context, event=None):
        label_name = context.scene.labels_regex
        SearchMark.marked_objects_hide = {}
        objects = mu.get_non_functional_objects()
        for obj in objects:
            if label_name in obj.name:
                bpy.context.scene.objects.active = bpy.data.objects[obj.name]
                bpy.data.objects[obj.name].select = True
                SearchMark.marked_objects_hide[obj.name] = bpy.data.objects[obj.name].hide
                bpy.data.objects[obj.name].hide = False
                bpy.data.objects[obj.name].active_material = bpy.data.materials['selected_label_Mat']
        SearchPanel.addon.show_rois()
        return {"FINISHED"}

bpy.types.Scene.labels_regex = bpy.props.StringProperty(default= '', description="labels regex")


class SearchPanel(bpy.types.Panel):
    bl_space_type = "GRAPH_EDITOR"
    bl_region_type = "UI"
    bl_context = "objectmode"
    bl_category = "Ohad"
    bl_label = "Search Panel"
    addon = None

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "labels_regex", text="Labels regex")
        row = layout.row(align=0)
        row.operator(SearchFilter.bl_idname, text="Search", icon = 'BORDERMOVE')
        row.operator(SearchMark.bl_idname, text="Mark", icon = 'GREASEPENCIL')
        layout.operator(SearchClear.bl_idname, text="Clear", icon = 'PANEL_CLOSE')


def init(addon):
    SearchPanel.addon = addon
    register()


def register():
    try:
        unregister()
        bpy.utils.register_class(SearchPanel)
        bpy.utils.register_class(SearchMark)
        bpy.utils.register_class(SearchClear)
        bpy.utils.register_class(SearchFilter)
        print('Search Panel was registered!')
    except:
        print("Can't register Search Panel!")


def unregister():
    try:
        bpy.utils.unregister_class(SearchPanel)
        bpy.utils.unregister_class(SearchMark)
        bpy.utils.unregister_class(SearchClear)
        bpy.utils.unregister_class(SearchFilter)
    except:
        print("Can't unregister Search Panel!")


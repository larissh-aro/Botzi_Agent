# tools_layer.py

from tools import (
    create_note, list_notes, update_note, delete_note,
)

class ToolsLayer:
    def create_note(self, **fields):
        return create_note.run(**fields)

    def delete_note(self, identifier):
        return delete_note.run(identifier)

    def update_note(self, identifier, fields):
        return update_note.run(identifier, fields)

    def list_notes(self):
        return list_notes.run()

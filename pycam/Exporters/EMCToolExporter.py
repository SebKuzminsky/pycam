import os

class EMCToolExporter:

    def __init__(self, tools):
        self.tools = tools

    def get_tool_definition_string(self):
        result = []
        #result.append(self.HEADER_ROW)
        for index in range(len(self.tools)):
            tool = self.tools[index]
            # use an arbitrary length
            tool_length = tool["tool_radius"] * 10
            line = "T%d P%d D%f Z-%f ;%s" % (index + 1, index + 1, 2 * tool["tool_radius"], tool_length, tool["name"])
            result.append(line)
        # add the dummy line for the "last" tool
        result.append("T99999 P99999 Z+0.100000 ;dummy tool")
        return os.linesep.join(result)


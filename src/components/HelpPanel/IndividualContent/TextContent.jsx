import React from "react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { CustomTable } from "./../MarkDownRenderers";

const TextContent = ({ content }) => (
  <Markdown
    children={content}
    remarkPlugins={[remarkGfm]}
    components={{
      table: CustomTable,
    }}
  />
);

export default TextContent;

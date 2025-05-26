import {
  Document,
  Paragraph,
  Table,
  TableCell,
  TableRow,
  TextRun,
  BorderStyle,
  WidthType,
  HeadingLevel,
  PageOrientation,
  SectionType,
  ImageRun,
} from "docx";

const addArchitectureDiagram = async (base64Data, children) => {
  if (!base64Data) return;

  try {
    children.push(
      new Paragraph({
        text: "Architecture Diagram",
        heading: HeadingLevel.HEADING_1,
        spacing: { before: 200, after: 100 },
      })
    );

    if (!base64Data) {
      return;
    }
    let imageData = base64Data;
    if (typeof base64Data === "object" && base64Data?.value) {
      imageData = base64Data.value;
    }

    if (typeof imageData === "string" && imageData.includes("base64,")) {
      imageData = imageData.split("base64,")[1];
    }

    try {
      let buffer;

      if (typeof Buffer !== "undefined") {
        buffer = Buffer.from(imageData, "base64");
      } else {
        const binaryString = atob(imageData);
        buffer = new Uint8Array(binaryString.length);
        for (let i = 0; i < binaryString.length; i++) {
          buffer[i] = binaryString.charCodeAt(i);
        }
      }

      children.push(
        new Paragraph({
          children: [
            new ImageRun({
              data: buffer,
              transformation: {
                width: 400,
                height: 300,
              },
              altText: "Architecture Diagram",
              description: "System Architecture Diagram",
            }),
          ],
          spacing: { before: 100, after: 200 },
        })
      );
    } catch (error) {
      console.error("Image conversion error:", error);
      children.push(
        new Paragraph({
          text: "[Image could not be processed]",
          spacing: { before: 100, after: 200 },
        })
      );
    }
  } catch (error) {
    console.error("Error adding diagram:", error);
    children.push(
      new Paragraph({
        text: "[Architecture diagram could not be displayed]",
        spacing: { before: 100, after: 200 },
      })
    );
  }
};

const createTableRow = (cells, isHeader = false) => {
  return new TableRow({
    children: cells.map(
      (text) =>
        new TableCell({
          children: Array.isArray(text)
            ? text.map(
                (item) =>
                  new Paragraph({
                    children: [
                      new TextRun({
                        text: `• ${item}`,
                        bold: isHeader,
                        size: isHeader ? 28 : 24,
                      }),
                    ],
                  })
              )
            : [
                new Paragraph({
                  children: [
                    new TextRun({
                      text: text?.toString() || "",
                      bold: isHeader,
                      size: isHeader ? 28 : 24,
                    }),
                  ],
                }),
              ],
          margins: { top: 0, bottom: 0, left: 0, right: 0 },
          borders: {
            top: { style: BorderStyle.SINGLE, size: 1 },
            bottom: { style: BorderStyle.SINGLE, size: 1 },
            left: { style: BorderStyle.SINGLE, size: 1 },
            right: { style: BorderStyle.SINGLE, size: 1 },
          },
        })
    ),
  });
};

const createTable = (headers, data) => {
  const formattedHeaders = headers.map((header) =>
    header
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  );

  const rows = [
    createTableRow(formattedHeaders, true),
    ...data.map((row) =>
      createTableRow(
        headers.map((header) => (Array.isArray(row[header]) ? row[header] : row[header]))
      )
    ),
  ];

  return new Table({
    width: {
      size: 100,
      type: WidthType.PERCENTAGE,
    },
    rows,
    margins: {
      top: 0,
      bottom: 0,
      right: 0,
      left: 0,
    },
  });
};

const createThreatModelingDocument = async (
  title,
  description,
  architectureDiagramBase64,
  assumptions,
  assets,
  dataFlowData,
  trustBoundaryData,
  threatSourceData,
  threatCatalogData
) => {
  const spacer = new Paragraph({
    text: "",
    spacing: { before: 100, after: 100 },
  });

  try {
    const mainChildren = [
      new Paragraph({
        text: title,
        heading: HeadingLevel.TITLE,
        spacing: { after: 200 },
      }),
    ];

    if (architectureDiagramBase64) {
      await addArchitectureDiagram(architectureDiagramBase64, mainChildren);
    }

    if (description?.length > 0) {
      mainChildren.push(
        new Paragraph({
          text: "Description",
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 200, after: 100 },
        })
      );

      const paragraphs = description.split("\n");

      paragraphs.forEach((paragraph) => {
        mainChildren.push(
          new Paragraph({
            text: paragraph,
            spacing: { before: 60, after: 60 },
          })
        );
      });

      mainChildren.push(spacer);
    }

    if (assumptions?.length > 0) {
      mainChildren.push(
        new Paragraph({
          text: "Assumptions",
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 200, after: 200 },
        }),
        createTable(["assumption"], assumptions),
        spacer
      );
    }

    if (assets?.length > 0) {
      mainChildren.push(
        new Paragraph({
          text: "Assets",
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 200, after: 200 },
        }),
        createTable(["type", "name", "description"], assets),
        spacer
      );
    }

    if (dataFlowData?.length > 0) {
      mainChildren.push(
        new Paragraph({
          text: "Data Flow",
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 200, after: 200 },
        }),
        createTable(["flow_description", "source_entity", "target_entity"], dataFlowData),
        spacer
      );
    }

    if (trustBoundaryData?.length > 0) {
      mainChildren.push(
        new Paragraph({
          text: "Trust Boundary",
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 200, after: 200 },
        }),
        createTable(["purpose", "source_entity", "target_entity"], trustBoundaryData),
        spacer
      );
    }

    if (threatSourceData?.length > 0) {
      mainChildren.push(
        new Paragraph({
          text: "Threat Source",
          heading: HeadingLevel.HEADING_1,
          spacing: { before: 200, after: 200 },
        }),
        createTable(["category", "description", "example"], threatSourceData),
        spacer
      );
    }

    const sections = [];

    sections.push({
      properties: {},
      children: mainChildren,
    });

    if (threatCatalogData?.length > 0) {
      const threatCatalogSection = {
        properties: {
          type: SectionType.NEXT_PAGE,
          page: {
            size: {
              orientation: PageOrientation.LANDSCAPE,
            },
          },
        },
        children: [
          new Paragraph({
            text: "Threat Catalog",
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 200, after: 200 },
          }),
          createTable(
            [
              "name",
              "stride_category",
              "description",
              "target",
              "impact",
              "likelihood",
              "mitigations",
            ],
            threatCatalogData
          ),
        ],
      };
      sections.push(threatCatalogSection);
    }

    const doc = new Document({
      sections: sections,
      styles: {
        paragraphStyles: [
          {
            id: "Title",
            name: "Title",
            run: {
              size: 36,
              bold: true,
              color: "000000",
            },
          },
          {
            id: "Heading1",
            name: "Heading 1",
            run: {
              size: 32,
              bold: true,
              color: "2E74B5",
            },
          },
        ],
      },
    });

    return doc;
  } catch (error) {
    console.error("Document creation failed:", error);
    throw new Error(`Failed to create document: ${error.message}`);
  }
};

export default createThreatModelingDocument;

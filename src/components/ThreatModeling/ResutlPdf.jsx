import React from "react";
import { jsPDF } from "jspdf";
import "jspdf-autotable";

export const createThreatModelingPDF = async (
  architectureDiagramBase64,
  title,
  description,
  assumptions,
  assets,
  dataFlowData,
  trustBoundaryData,
  threatSourceData,
  threatCatalogData
) => {
  const doc = new jsPDF();
  let yPos = 20;
  const pageHeight = doc.internal.pageSize.getHeight();
  const margin = 14;
  const pageWidth = doc.internal.pageSize.getWidth();
  const textWidth = pageWidth - (margin * 2);
  
  // Title
  doc.setFontSize(14);
  doc.text(title, 105, yPos, { align: "center" });
  yPos += 15;

  // Architecture diagram section
  if (architectureDiagramBase64) {
    try {
      let imageData = architectureDiagramBase64;
      if (typeof architectureDiagramBase64 === "object" && architectureDiagramBase64?.value) {
        imageData = `data:${architectureDiagramBase64.type};base64,${architectureDiagramBase64.value}`;
      }

      // Check if we need a new page for the diagram
      if (yPos > pageHeight - 40) {
        doc.addPage();
        yPos = 20;
      }

      doc.setFontSize(12);
      doc.text("Architecture Diagram", margin, yPos);
      yPos += 8;

      const img = new Image();
      await new Promise((resolve, reject) => {
        img.onload = resolve;
        img.onerror = reject;
        img.src = imageData;
      });

      const imgScale = 0.8;
      const imgWidth = Math.min(textWidth, img.width * imgScale);
      const imgHeight = (img.height * imgWidth) / img.width;
      
      // Check if diagram fits on current page
      if (yPos + imgHeight > pageHeight - margin) {
        doc.addPage();
        yPos = 20;
      }

      doc.addImage(imageData, "JPEG", margin, yPos, imgWidth, imgHeight);
      yPos += imgHeight + 8;
    } catch (error) {
      console.error("Error adding architecture diagram to PDF:", error);
      doc.setFontSize(10);
      doc.setTextColor(255, 0, 0);
      doc.text("Error: Could not load architecture diagram", margin, yPos);
      doc.setTextColor(0, 0, 0);
      yPos += 8;
    }
  }

  // Add text section with proper pagination
  const addTextSection = (sectionTitle, text) => {
    if (!text) return;
    
    // Check if we need a new page for section title
    if (yPos > pageHeight - 30) {
      doc.addPage();
      yPos = 20;
    }
    
    // Add section title
    doc.setFontSize(12);
    doc.text(sectionTitle, margin, yPos);
    yPos += 8;
    
    // Process text content with pagination
    doc.setFontSize(10);
    const lines = doc.splitTextToSize(text, textWidth);
    const lineHeight = 5;
    
    for (let i = 0; i < lines.length; i++) {
      // Check if we need a new page before adding this line
      if (yPos + lineHeight > pageHeight - margin) {
        doc.addPage();
        yPos = 20;
      }
      
      doc.text(lines[i], margin, yPos);
      yPos += lineHeight;
    }
    
    yPos += 8; // Space after section
  };

  // Add table section with proper pagination
  const addTableSection = (sectionTitle, data, columns, forceLandscape = false) => {
    if (!data || data.length === 0) return;
    
    if (forceLandscape) {
      // Add a new page in landscape orientation
      doc.addPage('a4', 'landscape');
      
      // Reset position for the new page
      yPos = 20;
      
      // Get new dimensions for landscape
      const landscapeWidth = doc.internal.pageSize.getWidth(); // Width in landscape
      const landscapeHeight = doc.internal.pageSize.getHeight(); // Height in landscape
      
      doc.setFontSize(12);
      doc.text(sectionTitle, margin, yPos);
      yPos += 8;
      
      doc.autoTable({
        startY: yPos,
        styles: { fontSize: 9, cellPadding: 2 },
        headStyles: {
          fontSize: 9,
          fontStyle: 'bold',
          halign: "left",
          cellPadding: 2,
        },
        head: [
          columns.map((col) =>
            col
              .split("_")
              .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
              .join(" ")
          ),
        ],
        body: data.map((row) =>
          columns.map((col) =>
            Array.isArray(row[col]) ? row[col].map((item) => `• ${item}`).join("\n") : row[col]
          )
        ),
        margin: { left: margin, right: margin },
        tableWidth: 'auto',
      });
    } else {
      // Regular table handling for portrait orientation
      if (yPos > pageHeight - 30) {
        doc.addPage();
        yPos = 20;
      }
      
      doc.setFontSize(12);
      doc.text(sectionTitle, margin, yPos);
      yPos += 8;
      
      doc.autoTable({
        startY: yPos,
        styles: { fontSize: 9, cellPadding: 2 },
        headStyles: {
          fontSize: 9,
          fontStyle: 'bold',
          halign: "left",
          cellPadding: 2,
        },
        head: [
          columns.map((col) =>
            col
              .split("_")
              .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
              .join(" ")
          ),
        ],
        body: data.map((row) =>
          columns.map((col) =>
            Array.isArray(row[col]) ? row[col].map((item) => `• ${item}`).join("\n") : row[col]
          )
        ),
        margin: { left: margin, right: margin },
        tableWidth: 'auto',
      });
      
      yPos = doc.lastAutoTable.finalY + 8;
    }
  };
  
  // Add sections in order
  if (description) {
    addTextSection("Description", description);
  }
  
  if (assumptions?.length > 0) {
    addTableSection("Assumptions", assumptions, ["assumption"]);
  }
  
  if (assets?.length > 0) {
    addTableSection("Assets", assets, ["type", "name", "description"]);
  }
  
  if (dataFlowData?.length > 0) {
    addTableSection("Data Flow", dataFlowData, ["flow_description", "source_entity", "target_entity"]);
  }
  
  if (trustBoundaryData?.length > 0) {
    addTableSection("Trust Boundary", trustBoundaryData, ["purpose", "source_entity", "target_entity"]);
  }
  
  if (threatSourceData?.length > 0) {
    addTableSection("Threat Source", threatSourceData, ["category", "description", "example"]);
  }
  
  // Add Threat Catalog in landscape mode
  if (threatCatalogData?.length > 0) {
    addTableSection("Threat Catalog", threatCatalogData, [
      "name",
      "stride_category",
      "description",
      "target",
      "impact",
      "likelihood",
      "mitigations",
    ], true); // true flag forces landscape mode
  }

  return doc;
};
import React, { useState, useEffect } from "react";
import Box from "@cloudscape-design/components/box";
import SpaceBetween from "@cloudscape-design/components/space-between";
import { Link } from "@cloudscape-design/components";
import Grid from "@cloudscape-design/components/grid";
import Container from "@cloudscape-design/components/container";
import Button from "@cloudscape-design/components/button";
import Header from "@cloudscape-design/components/header";
import { useNavigate } from "react-router";
import { S3DownloaderComponent } from "./S3Downloader";
import StatusIndicator from "@cloudscape-design/components/status-indicator";
import { Spinner, ButtonDropdown } from "@cloudscape-design/components";
import Badge from "@cloudscape-design/components/badge";
import {
  getThreatModelingStatus,
  getThreatModelingAllResults,
  deleteTm,
} from "../../services/ThreatDesigner/stats";


const StatusIndicatorComponent = ({ status }) => {
  switch (status) {
    case "COMPLETE":
      return <StatusIndicator type="success">Completed</StatusIndicator>;
    case "Not Found":
      return <StatusIndicator type="info">Unknown</StatusIndicator>;
    case "FAILED":
      return <StatusIndicator type="error">Failed</StatusIndicator>;
    case "LOADING":
      return (
        <SpaceBetween alignItems="center">
            <Spinner />
        </SpaceBetween>
      );
    default:
      return <StatusIndicator type="in-progress">In Progress</StatusIndicator>;
  }
};

const StatusComponponent = ({ id }) => {
  const [status, setStatus] = useState("LOADING");

  const handleRefresh = async () => {
    try {
      const statusResponse = await getThreatModelingStatus(id);
      setStatus(statusResponse.data.state);
    } catch (error) {
      console.error("Error fetching threat modeling status:", error);
      setStatus("FAILED");
    }
  };
  useEffect(() => {
    handleRefresh();
  }, []);

  return (
    <SpaceBetween direction="horizontal" size="s">
      <StatusIndicatorComponent status={status} />
      {["COMPLETE", "FAILED", "LOADING"].includes(status) || (
        <Button iconName="refresh" variant="inline-icon" onClick={handleRefresh} />
      )}
    </SpaceBetween>
  );
};

export const ThreatCatalogCardsComponent = ({ user }) => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const removeItem = (idToRemove) => {
    setResults(results.filter((item) => item.job_id !== idToRemove));
  };

  useEffect(() => {
    setLoading(true);
    const fetchAllResults = async () => {
      try {
        const results = await getThreatModelingAllResults();
        const sortedCatalogs = results?.data?.catalogs.sort((a, b) => {
          // Check if timestamp exists for both items
          if (!a.timestamp && !b.timestamp) return 0;
          if (!a.timestamp) return 1; // Push items without timestamp to the end
          if (!b.timestamp) return -1; // Push items without timestamp to the end

          return new Date(b.timestamp) - new Date(a.timestamp);
        });
        setResults(sortedCatalogs);
      } catch (error) {
        setResults([]);
        console.error("Error getting threat modeling results:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchAllResults();
  }, [user]);

  const navigate = useNavigate();

  const handleDelete = async (id) => {
    try {
      const results = await deleteTm(id);
      removeItem(id);
    } catch (error) {
      console.error("Error deleting threat model:", error);
    }
  };

  // Create a grid definition based on the number of items
  const createGridDefinition = () => {
    // Create a grid with 2 columns
    const gridDefinition = [];
    
    results.forEach(() => {
      gridDefinition.push({
        colspan: { default: 12, xxs: 12, xs: 12, s: 12, m: 6, l: 6, xl: 6 }
      });
    });
    
    return gridDefinition;
  };

  return (
    <SpaceBetween size="s">
      <Header variant="h1">Threat Catalog</Header>
      <div style={{ marginTop: 20 }}>
        {loading ? (
          <SpaceBetween alignItems="center">
            <Spinner size="large" />
          </SpaceBetween>
        ) : results.length > 0 ? (
          <Grid gridDefinition={createGridDefinition()}>
            {results.map((item) => (
              <div key={item.job_id} style={{ height: 250 }}>
                <Container 
                  key={item.job_id}
                  media={{
                    content: <S3DownloaderComponent fileName={item?.s3_location} />,
                    position: "side",
                    width: "40%"
                  }}
                  fitHeight
                  header={
                    <Header
                      variant="h2"
                      actions={
                        <ButtonDropdown
                          onItemClick={(itemClickDetails) => {
                            if (itemClickDetails.detail.id === "delete") {
                              handleDelete(item.job_id);
                            }
                          }}
                          items={[{ id: "delete", text: "Delete", disabled: false }]}
                          variant="icon"
                        />
                      }
                      style={{ width: '100%', overflow: 'hidden' }}
                    >
                        <Link 
                          fontSize="heading-m" 
                          onFollow={() => navigate(`/${item.job_id}`)}
                        >
                          {item?.title || "Untitled"}
                        </Link>
                    </Header>
                  }
                >
                  <div style={{ 
                    display: 'flex', 
                    flexDirection: 'column', 
                    height: '100%', 
                    justifyContent: 'space-between'
                  }}>
                    <div style={{ 
                      flex: 1,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'flex-start',
                      padding: '0 0 10px 0'
                    }}>
                      <Box 
                        variant="small" 
                        color="text-body-secondary"
                        style={{
                          overflow: 'hidden',
                          display: '-webkit-box',
                          WebkitLineClamp: 3,
                          WebkitBoxOrient: 'vertical',
                          textOverflow: 'ellipsis'
                        }}
                      >
                        {item?.summary || "No summary available"}
                      </Box>
                    </div>

                    <div>
                      <div style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'flex-start',
                        width: '100%'
                      }}>    
                        <div>
                          <Box variant="awsui-key-label">Status</Box>
                          <StatusComponponent id={item?.job_id} />
                        </div>                    
                        <div>
                          <Box variant="awsui-key-label" textAlign="left">Threats</Box>
                          <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                            <SpaceBetween direction="horizontal" size="xs">
                              <Badge color="severity-high">
                                {item?.threatCounts?.high || "-"}
                              </Badge>
                              <Badge color="severity-medium">
                                {item?.threatCounts?.medium || "-"}
                              </Badge>
                              <Badge color="severity-low">
                                {item?.threatCounts?.low || "-"}
                              </Badge>
                            </SpaceBetween>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </Container>
              </div>
            ))}
          </Grid>
        ) : (
          <Box margin={{ vertical: "xs" }} textAlign="center" color="inherit">
            <SpaceBetween size="m">
              <b>No threat model</b>
            </SpaceBetween>
          </Box>
        )}
      </div>
    </SpaceBetween>
  );

};

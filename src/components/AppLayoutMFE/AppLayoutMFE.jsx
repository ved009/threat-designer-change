import React, { useState, useEffect } from "react";
import { AppLayout, SplitPanel } from "@cloudscape-design/components";
import Main from "../../Main";
import "@cloudscape-design/global-styles/index.css";
import { useSplitPanel } from "../../SplitPanelContext";
import { useLocation } from "react-router-dom"; // Import useLocation from react-router-dom

const appLayoutLabels = {
  navigation: "Side navigation",
  navigationToggle: "Open side navigation",
  navigationClose: "Close side navigation",
};

function AppLayoutMFE({ user }) {
  const [navOpen, setNavOpen] = useState(true);
  const { splitPanelOpen, setSplitPanelOpen, splitPanelContext } = useSplitPanel();
  const location = useLocation(); // Get the current location

  // Effect to close split panel on route change
  useEffect(() => {
    setSplitPanelOpen(false);
  }, [location.pathname, setSplitPanelOpen]); // Dependency on location.pathname

  const renderSplitPanelContent = () => {
    if (splitPanelContext?.content) {
      return splitPanelContext.content;
    } else {
      return <></>;
    }
  };

  return (
    <div>
      {user && (
        <AppLayout
          disableContentPaddings={false}
          splitPanelSize={500}
          splitPanelOpen={splitPanelOpen}
          splitPanelPreferences={{ position: "side" }}
          onSplitPanelToggle={(event) => setSplitPanelOpen(event.detail.open)}
          splitPanel={
            <SplitPanel
              hidePreferencesButton={true}
              closeBehavior={"hide"}
              header={splitPanelContext?.context || "Details"}
            >
              {<renderSplitPanelContent />}
            </SplitPanel>
          }
          content={<Main user={user} />}
          navigationHide={true}
          toolsHide
          headerSelector={"#h"}
          ariaLabels={appLayoutLabels}
          navigationOpen={navOpen}
          onNavigationChange={() => setNavOpen(!navOpen)}
        />
      )}
    </div>
  );
}

export default AppLayoutMFE;

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Material
import QtQuick.Layouts
import QtQuick.Dialogs
import QtQuick.Effects

ApplicationWindow {
    id: window
    width: 1280
    height: 800
    minimumWidth: 1040
    minimumHeight: 680
    visible: true
    title: "Purrse — Monthly Money Journal"
    color: "#fff8fc"
    Material.theme: Material.Light
    Material.accent: "#e85da9"
    Material.primary: "#9a64d6"

    property color ink: "#493848"
    property color muted: "#877183"
    property color pink: "#ed70b6"
    property color purple: "#9b6add"
    property color coral: "#ff8b78"
    property color mint: "#70cfab"
    property color cream: "#fff8ef"
    property int currentPage: 0
    function moodPose(mood) { return mood === "celebrate" ? "celebrate" : mood === "happy" ? "wave" : mood === "gentle" ? "comfort" : "idle" }
    property string misoState: moodPose(Controller.summary.mood)
    property string misoMessage: Controller.summary.mascotMessage || "Ready when you are!"
    property bool celebration: false
    property var pendingDelete: null

    font.family: "Segoe UI"

    component SoftCard: Rectangle {
        radius: 22
        color: "white"
        border.color: "#f2e5ef"
        border.width: 1
        layer.enabled: GraphicsInfo.api !== GraphicsInfo.Software
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: "#250e1e2b"
            shadowBlur: 0.55
            shadowVerticalOffset: 4
        }
    }

    component PillButton: Button {
        id: control
        property color buttonColor: window.pink
        property color textColor: "white"
        implicitHeight: 42
        leftPadding: 18; rightPadding: 18
        font.pixelSize: 14
        font.weight: Font.DemiBold
        contentItem: Text {
            text: control.text
            color: control.textColor
            font: control.font
            horizontalAlignment: Text.AlignHCenter
            verticalAlignment: Text.AlignVCenter
        }
        background: Rectangle {
            radius: 15
            color: control.down ? Qt.darker(control.buttonColor, 1.12) : control.hovered ? Qt.lighter(control.buttonColor, 1.08) : control.buttonColor
            scale: control.down ? 0.96 : control.hovered ? 1.025 : 1
            Behavior on scale { enabled: !Controller.reducedMotion; SpringAnimation { spring: 5; damping: 0.32 } }
            Behavior on color { ColorAnimation { duration: 120 } }
        }
    }

    component MoneyCard: SoftCard {
        property string caption: ""
        property real targetValue: 0
        property real shownValue: 0
        property color accentColor: window.pink
        property string iconText: "✦"
        implicitHeight: 132
        onTargetValueChanged: shownValue = targetValue
        Behavior on shownValue { NumberAnimation { duration: Controller.reducedMotion ? 1 : 650; easing.type: Easing.OutCubic } }
        Column {
            anchors.fill: parent
            anchors.margins: 18
            spacing: 8
            Row {
                width: parent.width
                Text { text: parent.parent.parent.iconText; color: parent.parent.parent.accentColor; font.pixelSize: 21 }
                Text { text: parent.parent.parent.caption; color: window.muted; font.pixelSize: 13; anchors.verticalCenter: parent.verticalCenter; leftPadding: 8 }
            }
            Text {
                text: Number(parent.parent.shownValue / 1000).toLocaleString(Qt.locale("en_AU"), "f", Math.abs(parent.parent.shownValue % 1000) > 0 ? 1 : 0) + "k"
                color: window.ink; font.pixelSize: 27; font.weight: Font.Bold
            }
            Rectangle { width: 46; height: 5; radius: 3; color: parent.parent.accentColor }
        }
        HoverHandler { id: cardHover }
        scale: cardHover.hovered ? 1.02 : 1
        Behavior on scale { enabled: !Controller.reducedMotion; SpringAnimation { spring: 4; damping: 0.35 } }
    }

    Rectangle {
        anchors.fill: parent
        gradient: Gradient {
            orientation: Gradient.Horizontal
            GradientStop { position: 0; color: "#fff5fb" }
            GradientStop { position: 0.55; color: "#fcf8ff" }
            GradientStop { position: 1; color: "#f2fbff" }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 244
            Layout.fillHeight: true
            color: "#50344f"

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 18
                spacing: 10
                RowLayout {
                    Layout.fillWidth: true
                    Layout.bottomMargin: 18
                    Rectangle { width: 42; height: 42; radius: 15; color: "#ff8fc7"; Text { anchors.centerIn: parent; text: "🐾"; font.pixelSize: 22 } }
                    ColumnLayout {
                        spacing: 0
                        Text { text: "Purrse"; color: "white"; font.pixelSize: 24; font.weight: Font.Bold }
                        Text { text: "money, but cuter"; color: "#ddc8da"; font.pixelSize: 11 }
                    }
                    Item { Layout.fillWidth: true }
                }

                Repeater {
                    model: [
                        { icon: "⌂", label: "Overview" }, { icon: "≡", label: "Entries" },
                        { icon: "▣", label: "Monthly Gallery" }, { icon: "↗", label: "Reports" },
                        { icon: "⚙", label: "Settings" }
                    ]
                    delegate: Rectangle {
                        required property var modelData
                        required property int index
                        Layout.fillWidth: true
                        height: 48
                        radius: 15
                        color: window.currentPage === index ? "#22ffffff" : navMouse.containsMouse ? "#12ffffff" : "transparent"
                        Behavior on color { ColorAnimation { duration: 130 } }
                        Row { anchors.verticalCenter: parent.verticalCenter; leftPadding: 14; spacing: 13
                            Text { text: modelData.icon; color: index === window.currentPage ? "#ff98cd" : "#d9c6d7"; font.pixelSize: 21; width: 24; horizontalAlignment: Text.AlignHCenter }
                            Text { text: modelData.label; color: index === window.currentPage ? "white" : "#e5d9e3"; font.pixelSize: 14; font.weight: index === window.currentPage ? Font.DemiBold : Font.Normal }
                        }
                        MouseArea { id: navMouse; anchors.fill: parent; hoverEnabled: true; onClicked: window.goPage(index) }
                    }
                }
                Item { Layout.fillHeight: true }

                Rectangle {
                    id: companion
                    Layout.fillWidth: true
                    Layout.preferredHeight: 258
                    radius: 22
                    color: "#16ffffff"
                    clip: true

                    Rectangle {
                        anchors.top: parent.top; anchors.horizontalCenter: parent.horizontalCenter
                        anchors.topMargin: 10; width: parent.width - 24; height: 54; radius: 16
                        color: "#fff9fc"
                        Text { anchors.fill: parent; anchors.margins: 9; text: window.misoMessage; color: window.ink; font.pixelSize: 11; wrapMode: Text.WordWrap; horizontalAlignment: Text.AlignHCenter; verticalAlignment: Text.AlignVCenter }
                    }
                    Image {
                        id: misoImage
                        width: 178; height: 190
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        fillMode: Image.PreserveAspectFit
                        source: "../assets/miso/" + window.misoState + ".png"
                        asynchronous: true
                        transform: [
                            Translate { id: misoFloat; x: 0; y: 0 },
                            Scale { id: misoBreath; origin.x: misoImage.width / 2; origin.y: misoImage.height; xScale: 1; yScale: 1 },
                            Rotation { id: misoTilt; origin.x: misoImage.width / 2; origin.y: misoImage.height; angle: 0 }
                        ]
                        SequentialAnimation {
                            running: !Controller.reducedMotion && window.visible && window.visibility !== Window.Minimized
                            loops: Animation.Infinite
                            NumberAnimation { target: misoFloat; property: "y"; from: 2; to: -5; duration: 1150; easing.type: Easing.InOutSine }
                            NumberAnimation { target: misoFloat; property: "y"; from: -5; to: 2; duration: 1150; easing.type: Easing.InOutSine }
                        }
                        SequentialAnimation {
                            running: !Controller.reducedMotion && window.misoState === "celebrate"
                            loops: 2
                            NumberAnimation { target: misoImage; property: "scale"; to: 1.12; duration: 140; easing.type: Easing.OutBack }
                            NumberAnimation { target: misoImage; property: "scale"; to: 0.96; duration: 110 }
                            NumberAnimation { target: misoImage; property: "scale"; to: 1; duration: 120 }
                        }
                        SequentialAnimation {
                            running: !Controller.reducedMotion && ["idle","comfort","think","sleep"].indexOf(window.misoState) >= 0 && window.visibility !== Window.Minimized
                            loops: Animation.Infinite
                            ParallelAnimation {
                                NumberAnimation { target: misoBreath; property: "yScale"; from: 1; to: 1.025; duration: window.misoState === "sleep" ? 1350 : 850; easing.type: Easing.InOutSine }
                                NumberAnimation { target: misoBreath; property: "xScale"; from: 1; to: 0.99; duration: window.misoState === "sleep" ? 1350 : 850; easing.type: Easing.InOutSine }
                            }
                            ParallelAnimation {
                                NumberAnimation { target: misoBreath; property: "yScale"; to: 1; duration: window.misoState === "sleep" ? 1350 : 850; easing.type: Easing.InOutSine }
                                NumberAnimation { target: misoBreath; property: "xScale"; to: 1; duration: window.misoState === "sleep" ? 1350 : 850; easing.type: Easing.InOutSine }
                            }
                        }
                        SequentialAnimation {
                            running: !Controller.reducedMotion && window.misoState !== "sleep" && window.visibility !== Window.Minimized
                            loops: Animation.Infinite
                            NumberAnimation { target: misoTilt; property: "angle"; from: -1.3; to: 1.3; duration: 1250; easing.type: Easing.InOutSine }
                            NumberAnimation { target: misoTilt; property: "angle"; from: 1.3; to: -1.3; duration: 1250; easing.type: Easing.InOutSine }
                        }
                        SequentialAnimation {
                            running: !Controller.reducedMotion && window.misoState === "walk" && window.visibility !== Window.Minimized
                            loops: Animation.Infinite
                            NumberAnimation { target: misoFloat; property: "x"; from: -12; to: 12; duration: 750; easing.type: Easing.InOutQuad }
                            NumberAnimation { target: misoFloat; property: "x"; from: 12; to: -12; duration: 750; easing.type: Easing.InOutQuad }
                        }
                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: Controller.petMiso() }
                    }
                    Text { anchors.bottom: parent.bottom; anchors.right: parent.right; anchors.margins: 9; text: "click to pet ✨"; color: "#e6d4e3"; font.pixelSize: 9 }
                }
            }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 26
                spacing: 18

                RowLayout {
                    Layout.fillWidth: true
                    Text {
                        text: ["A bright little overview", "Entries, neatly gathered", "Monthly evidence gallery", "Reports & month close", "Make Purrse yours"][window.currentPage]
                        color: window.ink; font.pixelSize: 25; font.weight: Font.Bold
                    }
                    Item { Layout.fillWidth: true }
                    ToolButton {
                        text: Controller.soundEnabled ? "🔊" : "🔇"
                        font.pixelSize: 19
                        onClicked: Controller.saveSettings(!Controller.soundEnabled, Controller.soundVolume, Controller.reducedMotion)
                        ToolTip.visible: hovered; ToolTip.text: Controller.soundEnabled ? "Mute sounds" : "Enable sounds"
                    }
                    ComboBox {
                        id: monthPicker
                        model: Controller.monthLabels
                        currentIndex: Controller.currentMonthIndex
                        implicitWidth: 190
                        onActivated: Controller.currentMonthIndex = currentIndex
                    }
                }

                StackLayout {
                    id: pages
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: window.currentPage
                    opacity: 1
                    Behavior on opacity { NumberAnimation { duration: Controller.reducedMotion ? 50 : 230; easing.type: Easing.OutCubic } }

                    // Overview
                    ScrollView {
                        id: overviewScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: availableWidth
                        ColumnLayout {
                            width: overviewScroll.availableWidth
                            height: implicitHeight
                            spacing: 18
                            GridLayout {
                                Layout.fillWidth: true
                                columns: width > 900 ? 5 : 3
                                columnSpacing: 13; rowSpacing: 13
                                MoneyCard { Layout.fillWidth: true; caption: "Income"; targetValue: Controller.summary.income || 0; accentColor: window.mint; iconText: "↗" }
                                MoneyCard { Layout.fillWidth: true; caption: "Expenses"; targetValue: Controller.summary.expenses || 0; accentColor: window.coral; iconText: "↘" }
                                MoneyCard { Layout.fillWidth: true; caption: "Savings"; targetValue: Controller.summary.savings || 0; accentColor: window.purple; iconText: "✦" }
                                MoneyCard { Layout.fillWidth: true; caption: "Bank"; targetValue: Controller.summary.bank || 0; accentColor: "#53aee8"; iconText: "▤" }
                                MoneyCard { Layout.fillWidth: true; caption: "Debt"; targetValue: Controller.summary.debt || 0; accentColor: "#e66d8b"; iconText: "◒" }
                            }
                            RowLayout {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 330
                                spacing: 16
                                SoftCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout { anchors.fill: parent; anchors.margins: 20
                                        RowLayout { Layout.fillWidth: true
                                            Text { text: "Savings target"; color: window.ink; font.pixelSize: 17; font.weight: Font.DemiBold }
                                            Item { Layout.fillWidth: true }
                                            PillButton { text: "Edit"; buttonColor: "#f4e6f1"; textColor: window.purple; implicitHeight: 34; onClicked: targetDialog.openWithValue() }
                                        }
                                        Item { Layout.fillHeight: true; Layout.fillWidth: true
                                            Canvas { id: progressRing; anchors.centerIn: parent; width: 190; height: 190
                                                onPaint: { var c=getContext("2d"); c.reset(); c.lineWidth=18; c.strokeStyle="#f1e5ef"; c.beginPath(); c.arc(95,95,68,0,Math.PI*2); c.stroke(); c.strokeStyle="#a56de2"; c.lineCap="round"; c.beginPath(); c.arc(95,95,68,-Math.PI/2,-Math.PI/2+Math.PI*2*Math.min(1,(Controller.summary.targetPercent||0)/100)); c.stroke(); }
                                                Connections { target: Controller; function onSummaryChanged(){ progressRing.requestPaint() } }
                                            }
                                            Column { anchors.centerIn: parent; spacing: 2
                                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: Math.round(Controller.summary.targetPercent || 0) + "%"; color: window.purple; font.pixelSize: 30; font.weight: Font.Bold }
                                                Text { anchors.horizontalCenter: parent.horizontalCenter; text: (Controller.summary.savingsText || "0k") + " / " + (Controller.summary.targetText || "0k"); color: window.muted; font.pixelSize: 11 }
                                            }
                                        }
                                    }
                                }
                                SoftCard {
                                    Layout.fillWidth: true; Layout.fillHeight: true
                                    ColumnLayout { anchors.fill: parent; anchors.margins: 20; spacing: 10
                                        Text { text: "Miso’s monthly notes"; color: window.ink; font.pixelSize: 17; font.weight: Font.DemiBold }
                                        Repeater {
                                            model: Controller.summary.insights || []
                                            delegate: RowLayout { required property string modelData; required property int index; Layout.fillWidth: true
                                                Rectangle { width: 8; height: 8; radius: 4; color: index % 2 ? window.purple : window.pink }
                                                Text { Layout.fillWidth: true; text: modelData; color: window.ink; font.pixelSize: 13; wrapMode: Text.WordWrap }
                                            }
                                        }
                                        Item { Layout.fillHeight: true }
                                    }
                                }
                            }
                        }
                    }

                    // Entries
                    ColumnLayout {
                        spacing: 12
                        RowLayout { Layout.fillWidth: true
                            TextField { Layout.fillWidth: true; placeholderText: "Search categories or descriptions…"; leftPadding: 18; onTextChanged: Controller.searchEntries(text) }
                            PillButton { text: "+ Add entry"; onClicked: entryDialog.openNew() }
                        }
                        ListView {
                            id: entryList
                            Layout.fillWidth: true; Layout.fillHeight: true
                            model: Controller.entryModel
                            spacing: 10; clip: true
                            ScrollBar.vertical: ScrollBar {}
                            delegate: SoftCard {
                                required property int entryId
                                required property string entryDate
                                required property string entryKind
                                required property string category
                                required property string description
                                required property string amount
                                required property string amountRaw
                                required property int fileCount
                                width: entryList.width - 8; height: 82
                                RowLayout { anchors.fill: parent; anchors.margins: 15; spacing: 16
                                    Rectangle { width: 46; height: 46; radius: 16; color: entryKind === "income" ? "#dff8ec" : entryKind === "expense" ? "#ffe7df" : "#eee5fa"
                                        Text { anchors.centerIn: parent; text: entryKind === "income" ? "↗" : entryKind === "expense" ? "↘" : entryKind === "borrowed" ? "+D" : "−D"; color: window.ink; font.weight: Font.Bold }
                                    }
                                    ColumnLayout { Layout.fillWidth: true; spacing: 2
                                        Text { text: category; color: window.ink; font.pixelSize: 15; font.weight: Font.DemiBold }
                                        Text { text: entryDate + (description ? "  •  " + description : ""); color: window.muted; font.pixelSize: 12; elide: Text.ElideRight; Layout.fillWidth: true }
                                    }
                                    Text { visible: fileCount > 0; text: "📎 " + fileCount; color: window.muted; font.pixelSize: 12 }
                                    Text { text: amount; color: entryKind === "income" ? "#2b9b70" : entryKind === "expense" ? "#d65f59" : window.purple; font.pixelSize: 17; font.weight: Font.Bold }
                                    ToolButton { text: "✎"; onClicked: entryDialog.openEdit({id:entryId,date:entryDate,kind:entryKind,category:category,description:description,amount_raw:amountRaw}) }
                                    ToolButton { text: "×"; onClicked: confirmDialog.ask("Delete this entry and its managed attachment copies?", function(){ Controller.deleteEntry(entryId) }) }
                                }
                                HoverHandler { id: rowHover }
                                scale: rowHover.hovered ? 1.005 : 1
                                Behavior on scale { NumberAnimation { duration: 120 } }
                            }
                            footer: Item { width: 1; height: 12 }
                        }
                    }

                    // Gallery
                    ColumnLayout {
                        spacing: 12
                        RowLayout { Layout.fillWidth: true
                            ColumnLayout { spacing: 1
                                Text { text: "Images for the whole month"; color: window.ink; font.pixelSize: 18; font.weight: Font.DemiBold }
                                Text { text: "Balance screenshots and other evidence stay editable even after closing."; color: window.muted; font.pixelSize: 12 }
                            }
                            Item { Layout.fillWidth: true }
                            PillButton { text: "+ Add images"; onClicked: galleryFiles.open() }
                        }
                        GridView {
                            id: galleryGrid
                            Layout.fillWidth: true; Layout.fillHeight: true
                            model: Controller.galleryModel
                            cellWidth: 245; cellHeight: 276; clip: true
                            ScrollBar.vertical: ScrollBar {}
                            delegate: SoftCard {
                                id: galleryCard
                                required property int imageId
                                required property string originalName
                                required property string caption
                                required property url imageUrl
                                required property int sortOrder
                                width: 226; height: 258
                                ColumnLayout { anchors.fill: parent; anchors.margins: 11; spacing: 7
                                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 170; radius: 15; color: "#f6edf5"; clip: true
                                        Image { anchors.fill: parent; anchors.margins: 3; source: galleryCard.imageUrl; fillMode: Image.PreserveAspectCrop; asynchronous: true; cache: true }
                                        MouseArea { anchors.fill: parent; cursorShape: Qt.PointingHandCursor; onClicked: previewDialog.showImage(galleryCard.imageUrl, galleryCard.caption || galleryCard.originalName) }
                                    }
                                    Text { Layout.fillWidth: true; text: galleryCard.caption || galleryCard.originalName; color: window.ink; font.pixelSize: 12; font.weight: Font.DemiBold; elide: Text.ElideRight }
                                    RowLayout { Layout.fillWidth: true
                                        ToolButton { text: "←"; enabled: galleryCard.sortOrder > 0; onClicked: Controller.moveMonthImage(galleryCard.imageId, galleryCard.sortOrder - 1) }
                                        ToolButton { text: "→"; onClicked: Controller.moveMonthImage(galleryCard.imageId, galleryCard.sortOrder + 1) }
                                        Item { Layout.fillWidth: true }
                                        ToolButton { text: "✎"; onClicked: captionDialog.edit(galleryCard.imageId, galleryCard.caption) }
                                        ToolButton { text: "×"; onClicked: confirmDialog.ask("Remove this image from the monthly gallery?", function(){ Controller.deleteMonthImage(galleryCard.imageId) }) }
                                    }
                                }
                                DragHandler {
                                    id: galleryDrag
                                    target: null
                                    onActiveChanged: if (!active) {
                                        var p = galleryGrid.mapFromItem(galleryCard, centroid.position.x, centroid.position.y)
                                        var destination = galleryGrid.indexAt(p.x, p.y)
                                        if (destination >= 0 && destination !== galleryCard.sortOrder) Controller.moveMonthImage(galleryCard.imageId, destination)
                                    }
                                }
                            }
                            Text { anchors.centerIn: parent; visible: galleryGrid.count === 0; text: "Drop in a balance screenshot or add images above 🖼"; color: window.muted; font.pixelSize: 15 }
                            DropArea {
                                id: galleryDrop
                                anchors.fill: parent
                                onDropped: function(drop) { if (drop.hasUrls) Controller.addMonthImages(drop.urls) }
                                Rectangle { anchors.fill: parent; visible: galleryDrop.containsDrag; color: "#309b6add"; border.color: window.purple; border.width: 3; radius: 22
                                    Text { anchors.centerIn: parent; text: "Drop monthly images here ✨"; color: window.purple; font.pixelSize: 22; font.weight: Font.Bold }
                                }
                            }
                        }
                    }

                    // Reports
                    RowLayout {
                        spacing: 18
                        SoftCard {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout { anchors.fill: parent; anchors.margins: 24; spacing: 14
                                Text { text: "Beautiful monthly reports"; color: window.ink; font.pixelSize: 23; font.weight: Font.Bold }
                                Text { Layout.fillWidth: true; text: "Export the summary, entries, charts, curated monthly gallery, transaction receipts and personal reflection."; color: window.muted; font.pixelSize: 14; wrapMode: Text.WordWrap }
                                Rectangle { Layout.fillWidth: true; height: 1; color: "#f0e2ec" }
                                RowLayout { Layout.fillWidth: true
                                    PillButton { text: "Export DOCX"; onClicked: { reportSave.kind="docx"; reportSave.nameFilters=["Word document (*.docx)"]; reportSave.defaultSuffix="docx"; reportSave.open() } }
                                    PillButton { text: "Export PDF"; buttonColor: window.purple; onClicked: { reportSave.kind="pdf"; reportSave.nameFilters=["PDF document (*.pdf)"]; reportSave.defaultSuffix="pdf"; reportSave.open() } }
                                }
                                BusyIndicator { running: Controller.busy; visible: running }
                                Item { Layout.fillHeight: true }
                            }
                        }
                        SoftCard {
                            Layout.fillWidth: true; Layout.fillHeight: true
                            ColumnLayout { anchors.fill: parent; anchors.margins: 24; spacing: 13
                                Text { text: Controller.summary.status === "closed" ? "Month closed ✓" : "Ready for month-end?"; color: window.ink; font.pixelSize: 22; font.weight: Font.Bold }
                                Text { text: "Expected bank"; color: window.muted }
                                Text { text: Controller.summary.expectedBankText || "0k"; color: window.ink; font.pixelSize: 25; font.weight: Font.Bold }
                                Text { text: "Expected debt"; color: window.muted }
                                Text { text: Controller.summary.expectedDebtText || "0k"; color: window.ink; font.pixelSize: 25; font.weight: Font.Bold }
                                Item { Layout.fillHeight: true }
                                PillButton { Layout.fillWidth: true; text: Controller.summary.status === "closed" ? "Reopen month" : "Review & close month"; buttonColor: Controller.summary.status === "closed" ? "#a17bb8" : window.coral; onClicked: Controller.summary.status === "closed" ? confirmDialog.ask("Reopen this month for financial edits?", function(){Controller.reopenMonth()}) : closeDialog.open() }
                            }
                        }
                    }

                    // Settings
                    ScrollView {
                        contentWidth: availableWidth
                        ColumnLayout { width: parent.width; spacing: 16
                            SoftCard { Layout.fillWidth: true; implicitHeight: 230
                                ColumnLayout { anchors.fill: parent; anchors.margins: 22; spacing: 12
                                    Text { text: "Motion & sound"; color: window.ink; font.pixelSize: 20; font.weight: Font.Bold }
                                    Switch { id: soundSwitch; text: "Miso and interface sounds"; checked: Controller.soundEnabled; onToggled: Controller.saveSettings(checked, volumeSlider.value, motionSwitch.checked) }
                                    RowLayout { Layout.fillWidth: true
                                        Text { text: "Volume"; color: window.muted }
                                        Slider { id: volumeSlider; Layout.fillWidth: true; from: 0; to: 0.7; value: Controller.soundVolume; onMoved: Controller.saveSettings(soundSwitch.checked, value, motionSwitch.checked) }
                                    }
                                    Switch { id: motionSwitch; text: "Reduce motion"; checked: Controller.reducedMotion; onToggled: Controller.saveSettings(soundSwitch.checked, volumeSlider.value, checked) }
                                }
                            }
                            SoftCard { Layout.fillWidth: true; implicitHeight: 210
                                ColumnLayout { anchors.fill: parent; anchors.margins: 22; spacing: 12
                                    Text { text: "Data safety"; color: window.ink; font.pixelSize: 20; font.weight: Font.Bold }
                                    Text { text: "Create a ZIP backup of the database and all managed images and files."; color: window.muted; wrapMode: Text.WordWrap; Layout.fillWidth: true }
                                    RowLayout {
                                        PillButton { text: "Create backup"; onClicked: backupSave.open() }
                                        PillButton { text: "Restore backup"; buttonColor: "#ede1f4"; textColor: window.purple; onClicked: restoreOpen.open() }
                                        PillButton { text: "Open data folder"; buttonColor: "#e2f5ee"; textColor: "#278a67"; onClicked: Controller.openDataFolder() }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Celebration particles
    Repeater {
        model: window.celebration ? 28 : 0
        delegate: Rectangle {
            required property int index
            width: 8 + (index % 4) * 2; height: width; radius: index % 2 ? width / 2 : 2
            color: [window.pink, window.purple, window.coral, window.mint, "#ffd35a"][index % 5]
            x: window.width * (0.25 + ((index * 37) % 70) / 100)
            y: -20
            rotation: 0
            SequentialAnimation on y { running: true; NumberAnimation { to: window.height + 30; duration: 1100 + index * 24; easing.type: Easing.InQuad } }
            NumberAnimation on rotation { running: true; from: 0; to: 540; duration: 1200 }
        }
    }

    Timer { id: pageTimer; interval: Controller.reducedMotion ? 20 : 130; property int destination: 0; onTriggered: { window.currentPage=destination; pages.opacity=1 } }
    function goPage(index) { if (index === currentPage) return; pages.opacity=0; pageTimer.destination=index; pageTimer.restart() }

    Timer { id: moodReset; interval: 3900; onTriggered: { window.misoState = window.moodPose(Controller.summary.mood); window.misoMessage = Controller.summary.mascotMessage || "Ready when you are!"; window.celebration=false } }
    Timer { id: idleMiso; interval: 11000; repeat: true; running: !Controller.reducedMotion && window.visibility !== Window.Minimized
        onTriggered: { var states=["wave","walk","sleep","idle"]; window.misoState=states[Math.floor(Math.random()*states.length)]; window.misoMessage=window.misoState==="sleep" ? "Tiny nap… wake me for numbers." : "I’m keeping you company!"; moodReset.restart() }
    }
    Connections {
        target: Controller
        function onMascotEvent(state, message, sound) { window.misoState=state; window.misoMessage=message; window.celebration=state==="celebrate" && !Controller.reducedMotion; moodReset.restart() }
        function onNotice(title, message) { noticeDialog.title=title; noticeText.text=message; noticeDialog.open() }
    }

    Dialog { id: noticeDialog; anchors.centerIn: parent; width: 430; modal: true; standardButtons: Dialog.Ok
        contentItem: Text { id: noticeText; width: 380; wrapMode: Text.WordWrap; color: window.ink; font.pixelSize: 13 }
    }
    Dialog { id: confirmDialog; anchors.centerIn: parent; width: 430; modal: true; standardButtons: Dialog.Yes | Dialog.No
        property var callback
        property string prompt: ""
        function ask(text, action) { prompt=text; callback=action; open() }
        contentItem: Text { text: confirmDialog.prompt; wrapMode: Text.WordWrap; color: window.ink }
        onAccepted: if (callback) callback()
    }

    Dialog {
        id: setupDialog; anchors.centerIn: parent; width: 510; modal: true; closePolicy: Popup.NoAutoClose; title: "Welcome to Purrse"
        visible: Controller.needsSetup
        ColumnLayout { width: parent.width; spacing: 12
            Image { Layout.alignment: Qt.AlignHCenter; source: "../assets/miso/wave.png"; Layout.preferredWidth: 150; Layout.preferredHeight: 145; fillMode: Image.PreserveAspectFit }
            Text { text: "Meet Miso! Amounts are entered in thousand VND."; color: window.ink; Layout.alignment: Qt.AlignHCenter }
            TextField { id: setupBank; Layout.fillWidth: true; placeholderText: "Current bank balance (k VND)"; text: "0" }
            TextField { id: setupDebt; Layout.fillWidth: true; placeholderText: "Current debt (k VND)"; text: "0" }
            TextField { id: setupTarget; Layout.fillWidth: true; placeholderText: "Monthly savings target (k VND)"; text: "0" }
            PillButton { Layout.alignment: Qt.AlignRight; text: "Start sparkling ✨"; onClicked: Controller.setup(setupBank.text, setupDebt.text, setupTarget.text) }
        }
    }

    Dialog {
        id: entryDialog; anchors.centerIn: parent; width: 540; modal: true; title: editingId ? "Edit entry" : "Add entry"
        property int editingId: 0
        property var pendingFiles: []
        function openNew(){ editingId=0; dateField.text=Controller.suggestedDate(); kindBox.currentIndex=1; categoryField.text=""; amountField.text=""; descriptionField.text=""; pendingFiles=[]; open() }
        function openEdit(row){ editingId=row.id; dateField.text=row.date; kindBox.currentIndex=["income","expense","borrowed","repayment"].indexOf(row.kind); categoryField.text=row.category; amountField.text=row.amount_raw; descriptionField.text=row.description; pendingFiles=[]; open() }
        ColumnLayout { width: parent.width; spacing: 10
            TextField { id: dateField; Layout.fillWidth: true; placeholderText: "Date (DD-MM-YYYY)" }
            ComboBox { id: kindBox; Layout.fillWidth: true; model: ["income","expense","borrowed","repayment"] }
            TextField { id: categoryField; Layout.fillWidth: true; placeholderText: "Category" }
            TextField { id: amountField; Layout.fillWidth: true; placeholderText: "Amount (k VND)"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: descriptionField; Layout.fillWidth: true; placeholderText: "Description (optional)" }
            RowLayout { Layout.fillWidth: true
                PillButton { text: "Add files…"; buttonColor: "#eee2f4"; textColor: window.purple; onClicked: entryFiles.open() }
                Text { text: entryDialog.pendingFiles.length ? entryDialog.pendingFiles.length + " new file(s)" : "No new files"; color: window.muted }
            }
            RowLayout { Layout.fillWidth: true; Layout.topMargin: 10
                Item { Layout.fillWidth: true }
                PillButton { text: "Cancel"; buttonColor: "#efe8ee"; textColor: window.ink; onClicked: entryDialog.close() }
                PillButton { text: "Save entry"; onClicked: { if(entryDialog.editingId) Controller.updateEntry(entryDialog.editingId,dateField.text,kindBox.currentText,categoryField.text,amountField.text,descriptionField.text,entryDialog.pendingFiles); else Controller.addEntry(dateField.text,kindBox.currentText,categoryField.text,amountField.text,descriptionField.text,entryDialog.pendingFiles); entryDialog.close() } }
            }
        }
    }
    FileDialog { id: entryFiles; title: "Choose receipts or files"; fileMode: FileDialog.OpenFiles; onAccepted: entryDialog.pendingFiles=selectedFiles }
    FileDialog { id: galleryFiles; title: "Add monthly images"; fileMode: FileDialog.OpenFiles; nameFilters: ["Images (*.jpg *.jpeg *.png *.webp *.bmp *.tif *.tiff *.gif)"]; onAccepted: Controller.addMonthImages(selectedFiles) }

    Dialog { id: targetDialog; anchors.centerIn: parent; width: 390; modal: true; title: "Monthly savings target"
        function openWithValue(){ targetInput.text=Number((Controller.summary.target||0)/1000).toString(); open() }
        ColumnLayout { width: parent.width
            TextField { id: targetInput; Layout.fillWidth: true; placeholderText: "Target (k VND)" }
            PillButton { Layout.alignment: Qt.AlignRight; text: "Save target"; onClicked: { Controller.setTarget(targetInput.text); targetDialog.close() } }
        }
    }
    Dialog { id: closeDialog; anchors.centerIn: parent; width: 470; modal: true; title: "Month-end check"
        onOpened: { closeBank.text=Controller.summary.actualBankInput||"0"; closeDebt.text=Controller.summary.actualDebtInput||"0" }
        ColumnLayout { width: parent.width; spacing: 10
            Text { text: "Confirm actual balances. Differences remain visible as reconciliation adjustments."; wrapMode: Text.WordWrap; Layout.fillWidth: true; color: window.muted }
            TextField { id: closeBank; Layout.fillWidth: true; placeholderText: "Actual bank balance (k VND)" }
            TextField { id: closeDebt; Layout.fillWidth: true; placeholderText: "Actual debt (k VND)" }
            PillButton { Layout.alignment: Qt.AlignRight; text: "Close & roll forward"; buttonColor: window.coral; onClicked: { Controller.closeMonth(closeBank.text,closeDebt.text); closeDialog.close() } }
        }
    }
    Dialog { id: captionDialog; anchors.centerIn: parent; width: 430; modal: true; title: "Image caption"; property int imageId: 0
        function edit(id, value){ imageId=id; captionInput.text=value; open() }
        ColumnLayout { width: parent.width
            TextArea { id: captionInput; Layout.fillWidth: true; placeholderText: "Example: Closing bank balance — 30 September"; wrapMode: TextArea.Wrap }
            PillButton { Layout.alignment: Qt.AlignRight; text: "Save caption"; onClicked: { Controller.setMonthImageCaption(captionDialog.imageId,captionInput.text); captionDialog.close() } }
        }
    }
    Dialog { id: previewDialog; anchors.centerIn: parent; width: Math.min(window.width-100,900); height: Math.min(window.height-90,700); modal: true; property url imageSource; property string imageCaption
        function showImage(url,caption){ imageSource=url; imageCaption=caption; open() }
        ColumnLayout { anchors.fill: parent
            Image { Layout.fillWidth: true; Layout.fillHeight: true; source: previewDialog.imageSource; fillMode: Image.PreserveAspectFit; asynchronous: true }
            Text { Layout.fillWidth: true; text: previewDialog.imageCaption; color: window.ink; horizontalAlignment: Text.AlignHCenter; wrapMode: Text.WordWrap }
        }
    }

    FileDialog { id: reportSave; property string kind: "pdf"; title: "Export report"; fileMode: FileDialog.SaveFile; onAccepted: Controller.exportReport(kind,selectedFile) }
    FileDialog { id: backupSave; title: "Create Purrse backup"; fileMode: FileDialog.SaveFile; nameFilters: ["ZIP backup (*.zip)"]; defaultSuffix: "zip"; onAccepted: Controller.createBackup(selectedFile) }
    FileDialog { id: restoreOpen; title: "Restore Purrse backup"; fileMode: FileDialog.OpenFile; nameFilters: ["Purrse backup (*.zip)"]; onAccepted: confirmDialog.ask("Restore this backup? A safety backup of current data will be created first.", function(){Controller.restoreBackup(selectedFile)}) }
}

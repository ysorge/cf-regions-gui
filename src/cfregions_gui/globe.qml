import QtQuick
import QtQuick3D

Item {
    View3D {
        id: view
        anchors.fill: parent

        environment: SceneEnvironment {
            backgroundMode: SceneEnvironment.Color
            clearColor: controller.dark ? "#181a1d" : "#f2f3f4"
            antialiasingMode: SceneEnvironment.MSAA
            antialiasingQuality: SceneEnvironment.High
        }

        PerspectiveCamera {
            id: camera
            z: controller.camera_distance
            clipNear: 5
            clipFar: 1000
        }

        DirectionalLight {
            objectName: "globeLight"
            eulerRotation.x: -35
            eulerRotation.y: -25
            brightness: controller.dark ? 1.2 : 0.55
            ambientColor: controller.dark ? "#8a9298" : "#3d4346"
        }

        Node {
            eulerRotation.x: controller.rotation_x
            eulerRotation.y: controller.rotation_y

            Model {
                id: earth
                objectName: "earth"
                source: "#Sphere"
                scale: Qt.vector3d(2, 2, 2)
                pickable: true
                materials: [
                    PrincipledMaterial {
                        roughness: 0.9
                        metalness: 0.0
                        baseColorMap: Texture {
                            objectName: "globeTexture"
                            textureData: globeTextureData
                            // QImage rows start at the top, while Qt Quick 3D
                            // TextureData uses an OpenGL-style bottom-left UV origin.
                            flipV: true
                            generateMipmaps: true
                            mipFilter: Texture.Linear
                        }
                    }
                ]
            }
        }
    }

    MouseArea {
        id: mouseArea
        objectName: "globeMouseArea"
        anchors.fill: parent
        acceptedButtons: Qt.LeftButton
        hoverEnabled: true
        cursorShape: pressed ? Qt.ClosedHandCursor : Qt.OpenHandCursor
        property real previousX: 0
        property real previousY: 0
        property bool dragged: false
        property real dragDistance: 0
        property real hoverX: 0
        property real hoverY: 0
        property bool hoverDirty: false

        Timer {
            id: hoverTimer
            interval: 50
            repeat: true
            onTriggered: {
                if (!mouseArea.hoverDirty) {
                    stop()
                    return
                }
                mouseArea.hoverDirty = false
                var result = view.pick(mouseArea.hoverX, mouseArea.hoverY)
                if (result.objectHit === earth)
                    controller.hover_uv(result.uvPosition.x, result.uvPosition.y)
                else
                    controller.clear_hover()
            }
        }

        function scheduleHover(x, y) {
            hoverX = x
            hoverY = y
            hoverDirty = true
            if (!hoverTimer.running)
                hoverTimer.start()
        }

        onPressed: function(mouse) {
            hoverTimer.stop()
            hoverDirty = false
            controller.clear_hover()
            previousX = mouse.x
            previousY = mouse.y
            dragged = false
            dragDistance = 0
        }

        onPositionChanged: function(mouse) {
            if (!pressed) {
                scheduleHover(mouse.x, mouse.y)
                return
            }
            var dx = mouse.x - previousX
            var dy = mouse.y - previousY
            dragDistance += Math.sqrt(dx * dx + dy * dy)
            if (dragDistance > 3)
                dragged = true
            controller.rotate(dx, dy)
            previousX = mouse.x
            previousY = mouse.y
        }

        onReleased: function(mouse) {
            scheduleHover(mouse.x, mouse.y)
        }

        onClicked: function(mouse) {
            if (dragged)
                return
            var result = view.pick(mouse.x, mouse.y)
            if (result.objectHit === earth)
                controller.select_uv(result.uvPosition.x, result.uvPosition.y)
        }

        onDoubleClicked: function(mouse) {
            if (mouse.button !== Qt.LeftButton)
                return
            var result = view.pick(mouse.x, mouse.y)
            if (result.objectHit === earth)
                controller.activate_uv(result.uvPosition.x, result.uvPosition.y)
        }

        onExited: {
            hoverTimer.stop()
            hoverDirty = false
            controller.clear_hover()
        }

        onWheel: function(wheel) {
            controller.zoom_steps(wheel.angleDelta.y / 120)
            wheel.accepted = true
        }
    }
}

import numpy as np
import scipy as sp
import scipy.interpolate
import scipy.spatial
import vtk
import vtk.util.colors
import math
import warnings
warnings.filterwarnings("error")

class Plotter:
    COLOR_BG = vtk.util.colors.light_grey
    #vtk.util.colors.ivory
    COLOR_OBSTACLE = vtk.util.colors.banana
    COLOR_SITES = vtk.util.colors.cobalt
    COLOR_PATH = vtk.util.colors.brick
    COLOR_CONTROL_POINTS = vtk.util.colors.tomato
    COLOR_CONTROL_POLIG = vtk.util.colors.mint
    COLOR_GRAPH = vtk.util.colors.sepia

    _DEFAULT_LINE_THICKNESS = 0.05
    _DEFAULT_POINT_THICKNESS = 0.1
    _DEFAULT_BSPLINE_THICKNESS = 0.1

    def __init__(self):
        self._renderer = vtk.vtkRenderer()
        self._renderer.SetBackground(self.COLOR_BG)

        self._renderWindow = vtk.vtkRenderWindow()
        self._renderWindow.AddRenderer(self._renderer)
        self._renderWindowInteractor = vtk.vtkRenderWindowInteractor()
        self._renderWindowInteractor.SetRenderWindow(self._renderWindow)
        self._interactorStyle = vtk.vtkInteractorStyleUnicam()

    def draw(self):
        self._renderWindowInteractor.Initialize()
        self._renderWindowInteractor.SetInteractorStyle(self._interactorStyle)

        axes = vtk.vtkAxesActor()
        widget = vtk.vtkOrientationMarkerWidget()
        widget.SetOutlineColor(0.9300, 0.5700, 0.1300)
        widget.SetOrientationMarker(axes)
        widget.SetInteractor(self._renderWindowInteractor)
        widget.SetViewport(0.0, 0.0, 0.1, 0.1)
        widget.SetEnabled(True)
        widget.InteractiveOn()

        self._renderer.ResetCamera()
        camPos = self._renderer.GetActiveCamera().GetPosition()
        self._renderer.GetActiveCamera().SetPosition((camPos[2],camPos[1],camPos[0]))
        self._renderer.GetActiveCamera().SetViewUp((0.0,0.0,1.0))

        self._renderWindow.Render()
        self._renderWindowInteractor.Start()

    def addTetrahedron(self, vertexes, color):
        vtkPoints = vtk.vtkPoints()
        vtkPoints.InsertNextPoint(vertexes[0][0], vertexes[0][1], vertexes[0][2])
        vtkPoints.InsertNextPoint(vertexes[1][0], vertexes[1][1], vertexes[1][2])
        vtkPoints.InsertNextPoint(vertexes[2][0], vertexes[2][1], vertexes[2][2])
        vtkPoints.InsertNextPoint(vertexes[3][0], vertexes[3][1], vertexes[3][2])

        unstructuredGrid = vtk.vtkUnstructuredGrid()
        unstructuredGrid.SetPoints(vtkPoints)
        unstructuredGrid.InsertNextCell(vtk.VTK_TETRA, 4, range(4))

        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(unstructuredGrid)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)

        self._renderer.AddActor(actor)

    def addTriangles(self, triangles, color):
        vtkPoints = vtk.vtkPoints()
        idPoint = 0
        allIdsTriangle = []

        for triangle in triangles:
            idsTriangle = []

            for point in triangle:
                vtkPoints.InsertNextPoint(point[0], point[1], point[2])
                idsTriangle.append(idPoint)
                idPoint += 1

            allIdsTriangle.append(idsTriangle)

        unstructuredGrid = vtk.vtkUnstructuredGrid()
        unstructuredGrid.SetPoints(vtkPoints)
        for idsTriangle in allIdsTriangle:
            unstructuredGrid.InsertNextCell(vtk.VTK_TRIANGLE, 3, idsTriangle)

        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(unstructuredGrid)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)

        self._renderer.AddActor(actor)

    def addPolyLine(self, points, color, thick=False, thickness=_DEFAULT_LINE_THICKNESS):
        vtkPoints = vtk.vtkPoints()
        for point in points:
            vtkPoints.InsertNextPoint(point[0], point[1], point[2])

        if thick:
            cellArray = vtk.vtkCellArray()
            cellArray.InsertNextCell(len(points))
            for i in range(len(points)):
                cellArray.InsertCellPoint(i)

            polyData = vtk.vtkPolyData()
            polyData.SetPoints(vtkPoints)
            polyData.SetLines(cellArray)

            tubeFilter = vtk.vtkTubeFilter()
            tubeFilter.SetNumberOfSides(8)
            tubeFilter.SetInputData(polyData)
            tubeFilter.SetRadius(thickness)
            tubeFilter.Update()

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(tubeFilter.GetOutputPort())

        else:
            unstructuredGrid = vtk.vtkUnstructuredGrid()
            unstructuredGrid.SetPoints(vtkPoints)
            for i in range(1, len(points)):
                unstructuredGrid.InsertNextCell(vtk.VTK_LINE, 2, [i-1, i])

            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputData(unstructuredGrid)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)

        self._renderer.AddActor(actor)

    def addPoints(self, points, color, thick=False, thickness=_DEFAULT_POINT_THICKNESS):
        vtkPoints = vtk.vtkPoints()
        for point in points:
            vtkPoints.InsertNextPoint(point[0], point[1], point[2])

        pointsPolyData = vtk.vtkPolyData()
        pointsPolyData.SetPoints(vtkPoints)

        if thick:
            sphereSource = vtk.vtkSphereSource()
            sphereSource.SetRadius(thickness)
            
            glyph3D = vtk.vtkGlyph3D()
            glyph3D.SetSourceConnection(sphereSource.GetOutputPort())
            glyph3D.SetInputData(pointsPolyData)
            glyph3D.Update()
 
            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(glyph3D.GetOutputPort())
        else:
            vertexFilter = vtk.vtkVertexGlyphFilter()
            vertexFilter.SetInputData(pointsPolyData)
            vertexFilter.Update()                          

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputData(vertexFilter.GetOutput())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)

        self._renderer.AddActor(actor)

    def addBSpline(self, controlPolygon, degree, color, thick=False, thickness=_DEFAULT_BSPLINE_THICKNESS):
        x = controlPolygon[:,0]
        y = controlPolygon[:,1]
        z = controlPolygon[:,2]

        polLen = 0.
        for i in range(1, len(controlPolygon)):
            polLen += sp.spatial.distance.euclidean(controlPolygon[i-1], controlPolygon[i])

        l = len(x)
        t = np.linspace(0,1,l-degree+1,endpoint=True)
        t = np.append([0]*degree,t)
        t = np.append(t,[1]*degree)

        #[knots, coeff, degree]
        tck = [t,[x,y,z], degree]

        u=np.linspace(0,1,(max(polLen*100,100)),endpoint=True)
        out = sp.interpolate.splev(u, tck)
        outD1 = sp.interpolate.splev(u, tck, 1)
        outD2 = sp.interpolate.splev(u, tck, 2)
        outD3 = sp.interpolate.splev(u, tck, 3)

        spline = np.stack(out).T
        splineD1 = np.stack(outD1).T
        splineD2 = np.stack(outD2).T
        splineD3 = np.stack(outD3).T

        curvPlotActor = vtk.vtkXYPlotActor()
        curvPlotActor.SetTitle("Curvature")
        curvPlotActor.SetXTitle("")
        curvPlotActor.SetYTitle("")
        curvPlotActor.SetXValuesToIndex()
        
        torsPlotActor = vtk.vtkXYPlotActor()
        torsPlotActor.SetTitle("Torsion")
        torsPlotActor.SetXTitle("")
        torsPlotActor.SetYTitle("")
        torsPlotActor.SetXValuesToIndex()

        curvArray = vtk.vtkDoubleArray()
        torsArray = vtk.vtkDoubleArray()
        curvTorsArray = vtk.vtkDoubleArray()

        curvFieldData = vtk.vtkFieldData()
        torsFieldData = vtk.vtkFieldData()

        curvDataObject = vtk.vtkDataObject()
        torsDataObject = vtk.vtkDataObject()
        
        for i in range(len(u)):
            d1Xd2 = np.cross(splineD1[i], splineD2[i])
            Nd1Xd2 = np.linalg.norm(d1Xd2)
            
            currCurv = Nd1Xd2 / math.pow(np.linalg.norm(splineD1[i]),3)
            try:
                currTors = np.dot(d1Xd2, splineD3[i]) / math.pow(Nd1Xd2, 2)
            except RuntimeWarning:
                currTors = 0

            #currTors = np.linalg.det(np.stack([splineD1[i], splineD2[i], splineD3[i]]).T) / math.pow(np.linalg.norm(np.cross(splineD1[i], splineD2[i])), 2)
            
            curvArray.InsertNextValue(currCurv)
            torsArray.InsertNextValue(currTors)
            curvTorsArray.InsertNextValue(currCurv + abs(currTors))

        curvFieldData.AddArray(curvArray)
        curvDataObject.SetFieldData(curvFieldData)
        curvPlotActor.AddDataObjectInput(curvDataObject)
        
        torsFieldData.AddArray(torsArray)
        torsDataObject.SetFieldData(torsFieldData)
        torsPlotActor.AddDataObjectInput(torsDataObject)
        

        vtkPoints = vtk.vtkPoints()
        for point in spline:
            vtkPoints.InsertNextPoint(point[0], point[1], point[2])

        if thick:
            cellArray = vtk.vtkCellArray()
            cellArray.InsertNextCell(len(spline))
            for i in range(len(spline)):
                cellArray.InsertCellPoint(i)

            polyData = vtk.vtkPolyData()
            polyData.SetPoints(vtkPoints)
            polyData.SetLines(cellArray)

            polyData.GetPointData().SetScalars(curvTorsArray)
            
            tubeFilter = vtk.vtkTubeFilter()
            tubeFilter.SetNumberOfSides(8)
            tubeFilter.SetInputData(polyData)
            tubeFilter.SetRadius(thickness)
            tubeFilter.Update()

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(tubeFilter.GetOutputPort())

        else:
            unstructuredGrid = vtk.vtkUnstructuredGrid()
            unstructuredGrid.SetPoints(vtkPoints)
            for i in range(1, len(spline)):
                unstructuredGrid.InsertNextCell(vtk.VTK_LINE, 2, [i-1, i])

            unstructuredGrid.GetPointData().SetScalars(curvArray)
            
            mapper = vtk.vtkDataSetMapper()
            mapper.SetInputData(unstructuredGrid)

        self._curvPlotWidget = vtk.vtkXYPlotWidget()
        self._curvPlotWidget.SetXYPlotActor(curvPlotActor)
        self._curvPlotWidget.SetInteractor(self._renderWindowInteractor)
        self._curvPlotWidget.SetEnabled(True)

        self.torsPlotWidget = vtk.vtkXYPlotWidget()
        self.torsPlotWidget.SetXYPlotActor(torsPlotActor)
        self.torsPlotWidget.SetInteractor(self._renderWindowInteractor)
        self.torsPlotWidget.SetEnabled(True)
            
        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)

        self._renderer.AddActor(actor)


        #self.addPolyLine(list(zip(out[0], out[1], out[2])), color, thick, thickness)

    def addBSplineDEPRECATED(self, controlPolygon, degree, color, thick=False, thickness=_DEFAULT_BSPLINE_THICKNESS):
        x = controlPolygon[:,0]
        y = controlPolygon[:,1]
        z = controlPolygon[:,2]
    
        polLen = 0.
        for i in range(1, len(controlPolygon)):
            polLen += sp.spatial.distance.euclidean(controlPolygon[i-1], controlPolygon[i])

        t = range(len(controlPolygon))
        ipl_t = np.linspace(0.0, len(controlPolygon) - 1, max(polLen*100,100))

        x_tup = sp.interpolate.splrep(t, x, k = degree)
        y_tup = sp.interpolate.splrep(t, y, k = degree)
        z_tup = sp.interpolate.splrep(t, z, k = degree)

        x_list = list(x_tup)
        xl = x.tolist()
        x_list[1] = xl + [0.0, 0.0, 0.0, 0.0]

        y_list = list(y_tup)
        yl = y.tolist()
        y_list[1] = yl + [0.0, 0.0, 0.0, 0.0]

        z_list = list(z_tup)
        zl = z.tolist()
        z_list[1] = zl + [0.0, 0.0, 0.0, 0.0]

        x_i = sp.interpolate.splev(ipl_t, x_list)
        y_i = sp.interpolate.splev(ipl_t, y_list)
        z_i = sp.interpolate.splev(ipl_t, z_list)

        self.addPolyLine(list(zip(x_i, y_i, z_i)), color, thick, thickness)

    def addGraph(self, graph, color):
        vtkPoints = vtk.vtkPoints()
        vtkId = 0
        graph2VtkId = {}
        
        for node in graph.nodes():
            vtkPoints.InsertNextPoint(graph.node[node]['coord'][0], graph.node[node]['coord'][1], graph.node[node]['coord'][2])
            graph2VtkId[node] = vtkId
            vtkId += 1
            
        unstructuredGrid = vtk.vtkUnstructuredGrid()
        unstructuredGrid.SetPoints(vtkPoints)

        for edge in graph.edges():
            unstructuredGrid.InsertNextCell(vtk.VTK_LINE, 2, [graph2VtkId[edge[0]], graph2VtkId[edge[1]]])

        mapper = vtk.vtkDataSetMapper()
        mapper.SetInputData(unstructuredGrid)

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(color)

        self._renderer.AddActor(actor)
